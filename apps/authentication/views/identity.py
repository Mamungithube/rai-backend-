from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from ..serializers import (
    EmailChangeInitiateSerializer,
    EmailChangeVerifySerializer,
    PhoneChangeInitiateSerializer,
    PhoneChangeVerifySerializer,
)
from ..services import AuthService

CACHE_PENDING_TIMEOUT = 600  # 10 minutes


@extend_schema(request=EmailChangeInitiateSerializer, responses={200: dict}, summary="Initiate Email Change")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def initiate_email_change(request):
    serializer = EmailChangeInitiateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        new_email = serializer.validated_data['new_email']
        success, message, code = AuthService.initiate_otp(new_email, request)
        if success:
            cache.set(f"pending_email_change_{request.user.id}", new_email, CACHE_PENDING_TIMEOUT)
            return Response({"message": f"OTP sent to {new_email}"})
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
initiate_email_change.throttle_scope = 'otp'


@extend_schema(request=EmailChangeVerifySerializer, responses={200: dict}, summary="Verify Email Change")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def verify_email_change(request):
    serializer = EmailChangeVerifySerializer(data=request.data)
    if serializer.is_valid():
        new_email = cache.get(f"pending_email_change_{request.user.id}")
        if not new_email:
            return Response({"message": "Request expired."}, status=400)

        success, message, code = AuthService.verify_otp(
            new_email, serializer.validated_data['otp'], request
        )
        if success:
            user = request.user
            user.email = new_email
            user.save(update_fields=['email'])
            cache.delete(f"pending_email_change_{request.user.id}")
            return Response({"message": "Email updated successfully.", "email": new_email})
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
verify_email_change.throttle_scope = 'otp'


@extend_schema(request=None, responses={200: dict}, summary="Resend Email Change OTP")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def resend_email_change_otp(request):
    new_email = cache.get(f"pending_email_change_{request.user.id}")
    if not new_email:
        return Response({"message": "No pending request found."}, status=400)

    success, message, code = AuthService.initiate_otp(new_email, request)
    if success:
        return Response({"message": "OTP resent."})
    return Response({"message": message}, status=code)
resend_email_change_otp.throttle_scope = 'otp'


@extend_schema(request=PhoneChangeInitiateSerializer, responses={200: dict}, summary="Initiate Phone Change")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def initiate_phone_change(request):
    serializer = PhoneChangeInitiateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        new_phone = serializer.validated_data['new_phone']
        success, message, code = AuthService.initiate_otp(new_phone, request)
        if success:
            cache.set(f"pending_phone_change_{request.user.id}", new_phone, CACHE_PENDING_TIMEOUT)
            return Response({"message": f"OTP sent to {new_phone}"})
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
initiate_phone_change.throttle_scope = 'otp'


@extend_schema(request=PhoneChangeVerifySerializer, responses={200: dict}, summary="Verify Phone Change")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def verify_phone_change(request):
    serializer = PhoneChangeVerifySerializer(data=request.data)
    if serializer.is_valid():
        new_phone = cache.get(f"pending_phone_change_{request.user.id}")
        if not new_phone:
            return Response({"message": "Request expired or not found."}, status=400)

        success, message, code = AuthService.verify_otp(
            new_phone, serializer.validated_data['otp'], request
        )
        if success:
            user = request.user
            user.phone = new_phone
            user.save(update_fields=['phone'])
            cache.delete(f"pending_phone_change_{request.user.id}")
            return Response({"message": "Phone number updated successfully.", "phone": new_phone})
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
verify_phone_change.throttle_scope = 'otp'


@extend_schema(request=None, responses={200: dict}, summary="Resend Phone Change OTP")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def resend_phone_change_otp(request):
    new_phone = cache.get(f"pending_phone_change_{request.user.id}")
    if not new_phone:
        return Response({"message": "No pending request found."}, status=400)

    success, message, code = AuthService.initiate_otp(new_phone, request)
    if success:
        return Response({"message": "OTP resent."})
    return Response({"message": message}, status=code)
resend_phone_change_otp.throttle_scope = 'otp'
