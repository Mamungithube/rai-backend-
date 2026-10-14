import structlog
from rest_framework.decorators import api_view, throttle_classes, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from ..serializers import (
    SignupInitiateSerializer,
    SignupVerifySerializer,
    SignupFinalizeSerializer,
    ResendOTPSerializer,
    ProfileSerializer,
)
from ..services import AuthService

logger = structlog.get_logger(__name__)


@extend_schema(
    request=SignupInitiateSerializer,
    responses={200: dict, 400: dict},
    summary="Initiate Signup (Send OTP)"
)
@api_view(['POST'])
@throttle_classes([ScopedRateThrottle])
def signup_initiate(request):
    serializer = SignupInitiateSerializer(data=request.data)
    if serializer.is_valid():
        identifier = serializer.validated_data['identifier']
        success, message, code = AuthService.initiate_otp(identifier, request)
        if success:
            return Response({"identifier": identifier, "message": message}, status=code)
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
signup_initiate.throttle_scope = 'otp'


@extend_schema(
    request=SignupVerifySerializer,
    responses={200: dict, 400: dict},
    summary="Verify Signup OTP"
)
@api_view(['POST'])
@throttle_classes([ScopedRateThrottle])
def signup_verify(request):
    serializer = SignupVerifySerializer(data=request.data)
    if serializer.is_valid():
        success, message, code = AuthService.verify_otp(
            serializer.validated_data['identifier'],
            serializer.validated_data['otp'],
            request
        )
        if success:
            return Response({"message": message}, status=code)
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
signup_verify.throttle_scope = 'anon'


@extend_schema(
    request=SignupFinalizeSerializer,
    responses={201: dict, 400: dict},
    summary="Finalize Signup (Create User)"
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@throttle_classes([ScopedRateThrottle])
def signup_finalize(request):
    serializer = SignupFinalizeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        identifier = serializer.validated_data['identifier']
        user, message, code = AuthService.register_user(
            identifier,
            lambda: serializer.save()
        )

        if not user:
            return Response({"message": message}, status=code)

        tokens = AuthService.login_user(user)
        user_data = ProfileSerializer(user, context={'request': request}).data

        response_data = tokens
        response_data['user'] = user_data
        response_data['message'] = "Account created successfully."

        logger.info("user_registered", user_id=user.id)
        return Response(response_data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
signup_finalize.throttle_scope = 'anon'


@extend_schema(request=ResendOTPSerializer, responses={200: dict}, summary="Resend OTP")
@api_view(['POST'])
@throttle_classes([ScopedRateThrottle])
def resend_otp(request):
    serializer = ResendOTPSerializer(data=request.data)
    if serializer.is_valid():
        identifier = serializer.validated_data['identifier']
        success, message, code = AuthService.initiate_otp(identifier, request)
        if success:
            return Response({"message": "OTP resent successfully."})
        return Response({"message": message}, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
resend_otp.throttle_scope = 'otp'
