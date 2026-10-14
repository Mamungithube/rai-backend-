from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes, throttle_classes, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from ..serializers import ProfileSerializer, DeleteAccountSerializer

CACHE_PROFILE_TIMEOUT = 300  # 5 minutes


@extend_schema(responses={200: ProfileSerializer}, summary="Get Profile")
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def get_profile(request):
    cache_key = f"user_profile_{request.user.id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)

    serializer = ProfileSerializer(request.user, context={'request': request})
    data = serializer.data
    cache.set(cache_key, data, CACHE_PROFILE_TIMEOUT)
    return Response(data)
get_profile.throttle_scope = 'user'


@extend_schema(request=ProfileSerializer, responses={200: ProfileSerializer}, summary="Update Profile")
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@throttle_classes([ScopedRateThrottle])
def update_profile(request):
    serializer = ProfileSerializer(
        request.user,
        data=request.data,
        partial=True,
        context={'request': request}
    )
    if serializer.is_valid():
        serializer.save()
        cache.delete(f"user_profile_{request.user.id}")
        return Response({"message": "Profile updated successfully.", **serializer.data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
update_profile.throttle_scope = 'user'


@extend_schema(request=DeleteAccountSerializer, responses={200: dict}, summary="Delete Account")
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def delete_account(request):
    serializer = DeleteAccountSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Account deactivated."})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
delete_account.throttle_scope = 'user'
