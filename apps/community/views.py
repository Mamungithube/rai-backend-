from rest_framework.throttling import ScopedRateThrottle
import structlog
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Community, Membership, JoinRequest, CommunityMessage
from .serializers import (
    CommunityListSerializer, CommunityDetailSerializer, CreateCommunitySerializer,
    MembershipSerializer, CommunityMessageSerializer, AddMemberSerializer,
    JoinRequestSerializer, ChangeMemberRoleSerializer
)
from .services import CommunityService
from .permissions import IsCommunityAdmin

logger = structlog.get_logger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 30
    max_page_size = 100


class CommunityViewSet(viewsets.ModelViewSet):
    queryset = Community.objects.all()

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardPagination
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'community'

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'process_request', 'add_member', 'reset_invite_link', 'change_role', 'join_requests']:
            return [permissions.IsAuthenticated(), IsCommunityAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Community.objects.annotate(
            member_count=Count('memberships')
        ).order_by('-updated_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return CommunityListSerializer
        if self.action == 'create':
            return CreateCommunitySerializer
        return CommunityDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            community = CommunityService.create_community(
                request.user, serializer.validated_data)
        except Exception as e:
            logger.error("community_create_failed", error=str(e),
                         user_id=request.user.id, exc_info=True)
            return Response(
                {"detail": f"Failed to create community: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        detail_serializer = CommunityDetailSerializer(
            community, context={'request': request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({"message": "Community updated", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def join_requests(self, request, pk=None):
        community = self.get_object()
        requests = JoinRequest.objects.filter(
            community=community).select_related('user').order_by('-created_at')
        serializer = JoinRequestSerializer(
            requests, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='process_request')
    def process_request(self, request, pk=None):
        request_id = request.data.get('request_id')
        action_type = request.data.get('action')

        if not request_id or not action_type:
            return Response({"detail": "Missing data"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            success, msg = CommunityService.process_join_request(
                request.user, request_id, action_type)
        except Exception as e:
            logger.error("process_join_request_failed",
                         error=str(e), exc_info=True)
            return Response({"detail": "An error occurred processing the request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if success:
            return Response({"message": msg})
        return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='join_by_code')
    def join_by_code(self, request):
        code = request.data.get('invite_code')
        if not code:
            return Response({"detail": "Invite code required"}, status=status.HTTP_400_BAD_REQUEST)

        community, msg, code_status = CommunityService.join_by_code(
            request.user, code)

        if community:
            return Response({
                "message": msg,
                "community_id": str(community.id),
                "name": community.name
            }, status=code_status)

        return Response({"detail": msg}, status=code_status)

    @action(detail=True, methods=['post'], url_path='reset_invite_link')
    def reset_invite_link(self, request, pk=None):
        community = self.get_object()
        community.rotate_invite_code()
        return Response({
            "message": "Invite code reset",
            "invite_code": community.invite_code
        })

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        community = get_object_or_404(Community, pk=pk)
        if not Membership.objects.filter(community=community, user=request.user).exists():
            return Response({"detail": "Not a member"}, status=status.HTTP_403_FORBIDDEN)

        msgs = CommunityMessage.objects.filter(
            community=community).select_related('sender').order_by('-created_at')
        page = self.paginate_queryset(msgs)
        serializer = CommunityMessageSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        try:
            community = Community.objects.get(pk=pk)
        except Community.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if Membership.objects.filter(community=community, user=request.user).exists():
            return Response({"detail": "Already a member"}, status=status.HTTP_400_BAD_REQUEST)

        if community.is_private or community.approval_required:
            _, created = JoinRequest.objects.get_or_create(
                community=community, user=request.user)
            if created:
                return Response({"message": "Join request sent"})
            return Response({"detail": "You already have a pending request."}, status=status.HTTP_400_BAD_REQUEST)

        else:
            Membership.objects.create(
                community=community, user=request.user, role='member')
            return Response({"message": "Joined successfully"})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        community = self.get_object()
        try:
            with transaction.atomic():
                membership = Membership.objects.select_for_update().get(
                    community=community, user=request.user
                )
                is_admin = membership.role == 'admin'
                membership.delete()

                remaining = community.memberships.count()
                if remaining == 0:
                    community.delete()
                elif is_admin and not community.memberships.filter(role='admin').exists():
                    oldest_member = community.memberships.order_by(
                        'joined_at').first()
                    if oldest_member:
                        oldest_member.role = 'admin'
                        oldest_member.save(update_fields=['role'])

            return Response({"message": "Left community"})
        except Membership.DoesNotExist:
            return Response({"detail": "Not a member"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def toggle_mute(self, request, pk=None):
        community = self.get_object()
        try:
            membership = Membership.objects.get(
                community=community, user=request.user)
            membership.is_muted = not membership.is_muted
            membership.save()
            return Response({"message": "Mute status updated", "is_muted": membership.is_muted})
        except Membership.DoesNotExist:
            return Response({"detail": "Not a member"}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        community = self.get_object()
        search = request.query_params.get('search', '').strip()

        memberships = Membership.objects.filter(
            community=community).select_related('user')
        if search:
            memberships = memberships.filter(
                Q(user__username__icontains=search) | Q(
                    user__first_name__icontains=search)
            )

        memberships = memberships.order_by('role', 'user__username')
        page = self.paginate_queryset(memberships)
        serializer = MembershipSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        community = self.get_object()
        serializer = AddMemberSerializer(data=request.data)
        if serializer.is_valid():
            success, msg = CommunityService.add_member(
                community, request.user, serializer.validated_data['username_or_email']
            )
            if success:
                return Response({"message": msg})
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='change-role')
    def change_role(self, request, pk=None):
        community = self.get_object()
        serializer = ChangeMemberRoleSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target_user_id = serializer.validated_data['user_id']
        new_role = serializer.validated_data['role']

        if target_user_id == request.user.id:
            return Response({"detail": "You cannot change your own role here"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_membership = Membership.objects.get(
                community=community, user_id=target_user_id)
            target_membership.role = new_role
            target_membership.save()

            action_text = "promoted to Admin" if new_role == 'admin' else "demoted to Member"
            return Response({"message": f"User {action_text}"})

        except Membership.DoesNotExist:
            return Response({"detail": "User is not a member"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='upload-media')
    def upload_media(self, request, pk=None):
        community = get_object_or_404(Community, pk=pk)
        if not Membership.objects.filter(community=community, user=request.user).exists():
            return Response({"detail": "Not a member"}, status=status.HTTP_403_FORBIDDEN)

        image = request.FILES.get('image')
        audio = request.FILES.get('audio')

        if not image and not audio:
            return Response({"detail": "No media provided"}, status=status.HTTP_400_BAD_REQUEST)

        msg = CommunityService.create_message(
            community, request.user, image=image, audio=audio)
        image_url = request.build_absolute_uri(
            msg.image.url) if msg.image else None
        audio_url = request.build_absolute_uri(
            msg.audio.url) if msg.audio else None

        profile_pic_url = None
        if request.user.profile_picture:
            profile_pic_url = request.build_absolute_uri(
                request.user.profile_picture.url)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"community_{community.id}",
            {
                'type': 'chat_message',
                'id': str(msg.id),
                'message': "",
                'image': image_url,
                'audio': audio_url,
                'sender': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'profile_picture': profile_pic_url
                },
                'created_at': str(msg.created_at)
            }
        )

        return Response({
            "message": "Media uploaded",
            "data": {"image_url": image_url, "audio_url": audio_url, "message_id": str(msg.id)}
        })
