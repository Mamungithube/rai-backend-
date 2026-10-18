from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import IsAppAdmin
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from community.models import Community
from support.models import SupportTicket
from .models import AppPage
from .serializers import (
    AdminUserListSerializer,
    AdminCommunityListSerializer,
    AdminSupportTicketSerializer,
    AppPageSerializer
)
from config.utils import api_response

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


class AdminOverviewViewSet(viewsets.ViewSet):
    permission_classes = [IsAppAdmin]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Get Admin Dashboard Overview",
        description="Returns high-level overview metrics for Admin Dashboard: User Overview cards (Total, Free Plan, Plus, Premium), Growth Overview graph data (with filter: this_week, this_month, this_year), and Today's Subscribers / Recent Users table.",
        parameters=[
            OpenApiParameter(
                name="growth_filter",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Timeframe filter for growth chart (e.g. this_month, this_week, this_year)",
                default="this_month",
                required=False
            )
        ]
    )
    def list(self, request):
        now = timezone.now()

        # 1. Greeting & Admin Profile
        hour = now.hour
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        admin_user = request.user
        admin_name = f"{admin_user.first_name} {admin_user.last_name}".strip() or admin_user.username
        admin_photo = None
        if getattr(admin_user, 'profile_picture', None):
            url = admin_user.profile_picture.url
            admin_photo = url if url.startswith('http') else request.build_absolute_uri(url)

        # 2. User Overview Metrics
        users_qs = User.objects.filter(is_superuser=False)
        total_users = users_qs.count()
        active_users = users_qs.filter(is_active=True).count()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        new_users_today = users_qs.filter(created_at__gte=today_start).count()
        verified_users = users_qs.filter(Q(is_email_verified=True) | Q(is_phone_verified=True)).count()

        cards = [
            {
                "id": "total_user",
                "title": "Total User",
                "value": total_users,
                "subtitle": "Total registered user since",
                "icon": "users"
            },
            {
                "id": "free_user",
                "title": "Free Plan User",
                "value": total_users,
                "subtitle": "Total users who are using free plan",
                "icon": "user_check"
            },
            {
                "id": "plus_user",
                "title": "rai Plus User",
                "value": 0,
                "subtitle": "Total users who are using plus plan",
                "icon": "award"
            },
            {
                "id": "premium_user",
                "title": "rai Premium User",
                "value": 0,
                "subtitle": "Total users who are using premium plan",
                "icon": "crown"
            }
        ]

        # 3. Growth Overview (Chart)
        growth_filter = request.query_params.get('growth_filter', 'this_month')
        growth_labels = []
        growth_data = []

        if growth_filter == 'this_year':
            for m in range(1, now.month + 1):
                month_dt = timezone.datetime(now.year, m, 1)
                growth_labels.append(month_dt.strftime("%b"))
                m_count = users_qs.filter(created_at__year=now.year, created_at__month=m).count()
                growth_data.append(m_count)
        elif growth_filter == 'this_week':
            week_start = (now - timezone.timedelta(days=6)).date()
            cur_day = week_start
            while cur_day <= now.date():
                growth_labels.append(cur_day.strftime("%a"))
                d_count = users_qs.filter(created_at__date=cur_day).count()
                growth_data.append(d_count)
                cur_day += timezone.timedelta(days=1)
        else:  # 'this_month' (default)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
            cur_day = month_start
            while cur_day <= now.date():
                growth_labels.append(cur_day.strftime("%d %b"))
                d_count = users_qs.filter(created_at__date=cur_day).count()
                growth_data.append(d_count)
                cur_day += timezone.timedelta(days=1)

        # 4. Today's Subscribers / Recent Users List
        recent_users_qs = users_qs.order_by('-created_at')[:10]
        subscriber_list = []
        for idx, u in enumerate(recent_users_qs, start=1):
            photo_url = None
            if u.profile_picture:
                p_url = u.profile_picture.url
                photo_url = p_url if p_url.startswith('http') else request.build_absolute_uri(p_url)
            full_name = f"{u.first_name} {u.last_name}".strip() or u.username

            subscriber_list.append({
                "sl": f"{idx:02d}",
                "id": u.id,
                "username": u.username,
                "name": full_name,
                "photo": photo_url,
                "email": u.email or "N/A",
                "subscribed_plan": "Standard Free",
                "purchase_date": u.created_at.strftime("%d %b %y\n%I:%M %p"),
                "expire_date": "Lifetime / N/A",
                "status": "Active" if u.is_active else "Inactive",
                "is_active": u.is_active
            })

        return Response({
            "header": {
                "greeting": greeting,
                "admin_name": f"{admin_name}! 👋",
                "admin_photo": admin_photo
            },
            "user_overview": {
                "total_users": total_users,
                "active_users": active_users,
                "new_users_today": new_users_today,
                "verified_users": verified_users,
                "free_plan_users": total_users,
                "plus_users": 0,
                "premium_users": 0,
                "cards": cards
            },
            "growth_overview": {
                "current_filter": growth_filter,
                "available_filters": ["this_week", "this_month", "this_year"],
                "labels": growth_labels,
                "data": growth_data
            },
            "today_subscribers": subscriber_list,
            "recent_users": subscriber_list
        })


