from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from .models import CommentConcern
from .serializers import CommentConcernSerializer, AdminReplyCommentConcernSerializer


class CommentConcernPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CommentConcernViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentConcernSerializer
    pagination_class = CommentConcernPagination
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'user'

    def get_queryset(self):
        user = self.request.user
        if self.action in ['admin_list', 'reply'] and (user.is_staff or getattr(user, 'is_admin', False)):
            return CommentConcern.objects.select_related('user').order_by('-created_at')
        return CommentConcern.objects.filter(user=user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        pending_count = CommentConcern.objects.filter(
            user=request.user,
            status='pending'
        ).count()

        if pending_count >= 15:
            return Response(
                {"detail": "You have 15 pending comments/concerns. Please wait for them to be reviewed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            return Response(CommentConcernSerializer(instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reply(self, request, pk=None):
        instance = self.get_object()
        serializer = AdminReplyCommentConcernSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        admin_reply = serializer.validated_data['admin_reply']
        instance.admin_reply = admin_reply
        instance.status = 'replied'
        instance.replied_at = timezone.now()
        instance.save(update_fields=['admin_reply', 'status', 'replied_at'])

        # Send notification to user if notification app exists
        try:
            from notifications.services import send_notification
            send_notification(
                user=instance.user,
                title="Reply to your Comment & Concern",
                message=f"Admin replied to concern {instance.ticket_code}: {admin_reply[:100]}...",
                notification_type="comment_reply",
                reference_id=instance.ticket_code,
                extra_data={"ticket_code": instance.ticket_code, "comment_id": str(instance.id)}
            )
        except Exception:
            pass

        return Response({
            "message": "Reply sent successfully",
            "data": CommentConcernSerializer(instance).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser], url_path='admin-list')
    def admin_list(self, request):
        queryset = self.get_queryset()
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        page = self.paginate_queryset(queryset)
        serializer = CommentConcernSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
