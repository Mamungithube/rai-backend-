import structlog
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema

from ..serializers import MyTokenObtainPairSerializer, LogoutSerializer

logger = structlog.get_logger(__name__)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    @extend_schema(summary="Login (Get Tokens)")
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.data['message'] = "Login successful"
        logger.info("user_logged_in", username=request.data.get('username'))
        return response


@extend_schema(request=LogoutSerializer, responses={200: dict}, summary="Logout")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def logout_view(request):
    serializer = LogoutSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Logged out successfully."})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
logout_view.throttle_scope = 'user'
