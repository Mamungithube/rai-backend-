from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import IsAppAdmin
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination

from community.models import Community
from support.models import SupportTicket
from .models import AppPage
from .serializers import (
    AdminUserListSerializer,
    AdminCommunityListSerializer,
    AdminSupportTicketSerializer,
    AppPageSerializer
)
from Rai_Backend.utils import api_response

User = get_user_model()


class DashboardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [IsAppAdmin]
    serializer_class = AdminUserListSerializer
    pagination_class = DashboardPagination

    def get_queryset(self):
        queryset = User.objects.filter(
            is_superuser=False).order_by('-created_at')
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        return queryset

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Action to Ban/Unban user"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        status_text = "Active" if user.is_active else "Inactive"
        return api_response(message=f"User status changed to {status_text}", data={"status": status_text})


class AdminCommunityViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [IsAppAdmin]
    serializer_class = AdminCommunityListSerializer
    pagination_class = DashboardPagination

    def get_queryset(self):
        queryset = Community.objects.annotate(
            member_count=Count('memberships')
        ).order_by('-created_at')

        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response(message="Community deleted successfully", status_code=200)


class AdminSupportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [IsAppAdmin]
    serializer_class = AdminSupportTicketSerializer
    pagination_class = DashboardPagination
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        queryset = SupportTicket.objects.select_related(
            'user').order_by('-created_at')
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(message__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search)
            )
        return queryset

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        admin_response = request.data.get('admin_response')

        if not admin_response:
            return Response(
                {"detail": "admin_response is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.admin_response = admin_response
        instance.status = 'resolved'
        instance.replied_at = timezone.now()
        instance.save(update_fields=['admin_response', 'status', 'replied_at'])
        return api_response(message="Reply sent successfully", status_code=200)


class AdminPageSettingsViewSet(viewsets.ModelViewSet):
    queryset = AppPage.objects.all()
    serializer_class = AppPageSerializer
    lookup_field = 'slug'
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            return [permissions.AllowAny()]
        return [IsAppAdmin()]

    @action(detail=True, methods=['post', 'patch'])
    def update_content(self, request, slug=None):
        page = self.get_object()
        content = request.data.get('content')

        if not content:
            return api_response(message="Content cannot be empty", success=False, status_code=400)

        page.content = content
        page.save(update_fields=['content'])
        return api_response(message=f"{page.title} updated successfully")
