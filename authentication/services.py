import structlog
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, OTP
from .otp_service import generate_otp, send_otp
from Rai_Backend.utils import get_client_ip

logger = structlog.get_logger(__name__)


class AuthService:

    @staticmethod
    def normalize_identifier(identifier):
        identifier = identifier.strip()
        if "@" in identifier:
            return identifier.lower()
        return identifier

    @staticmethod
    def initiate_otp(identifier, request=None):
        identifier = AuthService.normalize_identifier(identifier)
        rate_limit_key = f"otp_limit_{identifier}"
        if cache.get(rate_limit_key):
            return False, "Please wait before requesting another OTP.", 429

        method = "email" if "@" in identifier else "sms"

        try:
            with transaction.atomic():
                OTP.objects.filter(identifier=identifier).delete()
                otp_code = generate_otp()
                OTP.objects.create(
                    identifier=identifier,
                    code=otp_code,
                    is_verified=False
                )
        except Exception as e:
            logger.error("otp_generation_failed", error=str(e))
            return False, "System error generating OTP.", 500

        send_result = send_otp(identifier, otp_code, method=method)

        if not send_result:
            OTP.objects.filter(identifier=identifier).delete()
            return False, "Failed to send OTP. Please try again.", 500

        cache.set(rate_limit_key, True, 60)
        return True, "OTP sent successfully.", 200

    @staticmethod
    def verify_otp(identifier, otp_input, request=None):
        identifier = AuthService.normalize_identifier(identifier)
        otp_record = OTP.objects.filter(identifier=identifier).order_by('-created_at').first()

        if not otp_record:
            return False, "No OTP found. Please request a new one.", 400

        if not otp_record.is_valid():
            return False, "OTP has expired or max attempts reached.", 400

        if request:
            client_ip = get_client_ip(request)
            ip_key = f"otp_verify_attempt_{identifier}_{client_ip}"
            attempts = cache.get(ip_key, 0)
            if attempts >= 5:
                return False, "Too many attempts. Try again in 5 minutes.", 429
            cache.set(ip_key, attempts + 1, 300)

        if not constant_time_compare(otp_record.code, otp_input):
            otp_record.increment_attempts()
            remaining = 5 - otp_record.attempts
            return False, f"Invalid OTP. {remaining} attempts remaining.", 400

        otp_record.is_verified = True
        otp_record.save(update_fields=['is_verified'])

        if request:
            cache.delete(f"otp_verify_attempt_{identifier}_{get_client_ip(request)}")

        return True, "OTP verified successfully.", 200

    @staticmethod
    def register_user(identifier, create_user_fn):
        identifier = AuthService.normalize_identifier(identifier)
        otp_record = OTP.objects.filter(identifier=identifier, is_verified=True).first()
        if not otp_record:
            return None, "OTP not verified. Please verify first.", 403

        try:
            with transaction.atomic():
                user = create_user_fn()
                OTP.objects.filter(identifier=identifier).delete()

            return user, "User created", 201

        except IntegrityError as e:
            logger.error("registration_integrity_error", error=str(e))
            return None, "An account with this information already exists.", 400

        except Exception as e:
            if hasattr(e, 'detail'):
                return None, e.detail, 400

            logger.error("registration_failed", error=str(e))
            return None, "Database error during registration.", 500

    @staticmethod
    def login_user(user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "username": user.username
        }