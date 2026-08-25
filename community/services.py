import structlog
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Community, Membership, JoinRequest, CommunityMessage

logger = structlog.get_logger(__name__)
User = get_user_model()


class CommunityService:

    @staticmethod
    def create_community(user, validated_data):
        try:
            with transaction.atomic():
                community = Community.objects.create(**validated_data)
                Membership.objects.create(
                    community=community,
                    user=user,
                    role='admin'
                )
            logger.info("community_created", community_id=str(
                community.id), user_id=user.id)
            return community
        except Exception as e:
            logger.error(
                "community_create_db_error",
                error=str(e),
                error_type=type(e).__name__,
                user_id=user.id,
                exc_info=True,
            )
            raise

    @staticmethod
    def join_by_code(user, invite_code):
        try:
            community = Community.objects.get(invite_code=invite_code)
        except Community.DoesNotExist:
            return None, "Invalid invite code", 404

        if Membership.objects.filter(community=community, user=user).exists():
            return None, "Already a member", 400

        Membership.objects.create(
            community=community, user=user, role='member')
        JoinRequest.objects.filter(community=community, user=user).delete()

        logger.info("user_joined_via_code", community_id=str(
            community.id), user_id=user.id)
        return community, "Joined successfully", 200

    @staticmethod
    def process_join_request(admin_user, request_id, action):
        join_req = get_object_or_404(JoinRequest, id=request_id)

        if not Membership.objects.filter(community=join_req.community, user=admin_user, role='admin').exists():
            return False, "Permission denied"

        if action == 'approve':
            Membership.objects.get_or_create(
                community=join_req.community,
                user=join_req.user,
                defaults={'role': 'member'}
            )
            join_req.delete()
            return True, "User approved"

        elif action == 'reject':
            join_req.delete()
            return True, "User rejected"

        return False, "Invalid action"

    @staticmethod
    def add_member(community, admin_user, username_or_email):
        if not Membership.objects.filter(community=community, user=admin_user, role='admin').exists():
            return False, "Permission denied"

        try:
            user_to_add = User.objects.get(
                Q(username=username_or_email) | Q(email=username_or_email))
        except User.DoesNotExist:
            return False, "User not found"

        if Membership.objects.filter(community=community, user=user_to_add).exists():
            return False, "User already in group"

        Membership.objects.create(
            community=community, user=user_to_add, role='member')
        JoinRequest.objects.filter(
            community=community, user=user_to_add).delete()

        return True, "Member added"

    @staticmethod
    def create_message(community, user, text=None, image=None, audio=None):
        msg = CommunityMessage.objects.create(
            community=community,
            sender=user,
            text=text or "",
            image=image,
            audio=audio
        )
        Community.objects.filter(pk=community.pk).update(
            updated_at=timezone.now())
        return msg
