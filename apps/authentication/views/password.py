from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from ..serializers import (
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
)
from ..services import AuthService


@extend_schema(request=PasswordResetRequestSerializer, responses={200: dict}, summary="Request Password Reset")
@api_view(['POST'])
@throttle_classes([ScopedRateThrottle])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        identifier = serializer.validated_data['identifier']
        success, message, code = AuthService.initiate_otp(identifier, request)
        if success:
            return Response({"message": "If account exists, OTP sent."}, status=200)
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
password_reset_request.throttle_scope = 'otp'


@extend_schema(request=PasswordResetConfirmSerializer, responses={200: dict}, summary="Confirm Password Reset")
@api_view(['POST'])
@throttle_classes([ScopedRateThrottle])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Password reset successfully."})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
password_reset_confirm.throttle_scope = 'anon'


@extend_schema(request=PasswordChangeSerializer, responses={200: dict}, summary="Change Password")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def change_password(request):
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Password changed successfully."})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
change_password.throttle_scope = 'user'
