from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.pagination import PageNumberPagination
from .models import Notification
from .serializers import NotificationSerializer


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'user'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        return Response({"message": "Marked as read", "is_read": True}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        updated_count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({
            "message": f"All {updated_count} notifications marked as read.",
            "updated_count": updated_count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_read(self, request):
        deleted_count, _ = Notification.objects.filter(user=request.user, is_read=True).delete()
        return Response({
            "message": f"Cleared {deleted_count} read notifications.",
            "deleted_count": deleted_count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='fcm-token')
    def register_fcm_token(self, request):
        fcm_token = request.data.get('fcm_token')
        device_type = request.data.get('device_type', 'android').lower()

        if not fcm_token or not fcm_token.strip():
            return Response({"detail": "fcm_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import FCMDevice
        device, created = FCMDevice.objects.update_or_create(
            fcm_token=fcm_token.strip(),
            defaults={
                'user': request.user,
                'device_type': device_type if device_type in ['android', 'ios', 'web'] else 'android',
                'is_active': True,
            }
        )
        return Response({
            "message": "FCM device token registered successfully.",
            "device_id": str(device.id),
            "device_type": device.device_type,
            "is_active": device.is_active
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post', 'delete'], url_path='fcm-token/remove')
    def remove_fcm_token(self, request):
        fcm_token = request.data.get('fcm_token')
        if not fcm_token or not fcm_token.strip():
            return Response({"detail": "fcm_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import FCMDevice
        updated = FCMDevice.objects.filter(fcm_token=fcm_token.strip(), user=request.user).update(is_active=False)
        return Response({
            "message": "FCM device token removed/deactivated.",
            "success": updated > 0
        }, status=status.HTTP_200_OK)
