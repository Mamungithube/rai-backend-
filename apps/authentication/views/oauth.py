import structlog
import requests as http_requests
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.db import transaction, IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from ..serializers import ProfileSerializer
from ..models import User

logger = structlog.get_logger(__name__)


@extend_schema(
    request={"application/json": {"type": "object", "properties": {"id_token": {"type": "string"}}}},
    responses={200: dict, 400: dict, 401: dict},
    summary="Google Login / Sign-Up"
)
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        token_str = request.data.get("id_token")
        if not token_str:
            return Response({"detail": "id_token is required"}, status=400)

        try:
            decoded = {}
            if token_str.startswith("ya29"):
                user_info_resp = http_requests.get(
                    f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token_str}"
                )
                user_info_resp.raise_for_status()
                decoded = user_info_resp.json()
            else:
                decoded = google_id_token.verify_oauth2_token(
                    token_str,
                    google_requests.Request(),
                    settings.GOOGLE_CLIENT_ID
                )
                if decoded.get("aud") != settings.GOOGLE_CLIENT_ID:
                    return Response({"detail": "Invalid token audience"}, status=401)

            if not decoded.get("email_verified", False):
                return Response({"detail": "Google email not verified"}, status=401)

            email = decoded.get("email")
            if not email:
                return Response({"detail": "Email not provided by Google"}, status=400)

            with transaction.atomic():
                existing = User.objects.filter(email=email).first()
                if existing:
                    user = existing
                    created = False
                else:
                    base = email.split("@")[0].lower()
                    username = base
                    suffix = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base}{suffix}"
                        suffix += 1

                    user = User.objects.create(
                        email=email,
                        username=username,
                        is_active=True,
                        is_email_verified=True,
                    )
                    user.set_unusable_password()
                    user.save(update_fields=['password'])
                    created = True

            if not user.is_active:
                return Response({"detail": "Account is disabled"}, status=403)

            tokens = user.tokens
            logger.info("google_login", user_id=user.id, created=created)
            return Response({
                "message": "Login successful",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": ProfileSerializer(user, context={"request": request}).data
            }, status=200)

        except ValueError:
            return Response({"detail": "Invalid or expired Google token"}, status=401)
        except http_requests.exceptions.RequestException:
            return Response({"detail": "Failed to validate token with Google"}, status=400)
        except IntegrityError:
            logger.exception("google_auth_integrity_error")
            return Response({"detail": "Account creation failed. Please try again."}, status=400)
        except Exception:
            logger.exception("google_auth_error")
            return Response({"detail": "Google authentication failed"}, status=400)
