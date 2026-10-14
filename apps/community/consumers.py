import json
import structlog
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from .models import Community, Membership, CommunityMessage

logger = structlog.get_logger(__name__)

MAX_MESSAGE_LENGTH = 5000


class CommunityConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            logger.warning("community_ws_rejected_anonymous")
            await self.close(code=4001)
            return

        self.community_id = self.scope["url_route"]["kwargs"]["community_id"]
        self.room_group_name = f"community_{self.community_id}"

        membership = await self.get_membership(self.community_id, self.user)
        if not membership:
            logger.warning(
                "community_ws_unauthorized",
                user_id=self.user.id,
                community_id=self.community_id,
            )
            await self.close(code=4003)
            return

        self.is_muted = membership.is_muted

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        self.base_url = getattr(settings, "SERVER_BASE_URL", "")

        try:
            history = await self.get_chat_history(self.community_id, self.base_url)
            await self.send(text_data=json.dumps({"type": "history", "messages": history}))
        except Exception as e:
            logger.error("community_ws_history_failed", error=str(e), exc_info=True)
            await self.send(text_data=json.dumps({"type": "history", "messages": []}))

        logger.info("community_ws_connected", user_id=self.user.id, community_id=self.community_id)

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info("community_ws_disconnected", user_id=getattr(self.user, "id", None), code=close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as e:
            logger.warning("community_ws_invalid_json", error=str(e))
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON."}))
            return

        try:
            message_text = data.get("message", "").strip()
            if not message_text:
                return

            if len(message_text) > MAX_MESSAGE_LENGTH:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.",
                }))
                return

            membership = await self.get_membership(self.community_id, self.user)
            if not membership:
                await self.send(text_data=json.dumps({"type": "error", "message": "You are no longer a member."}))
                return

            if membership.is_muted:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "You are muted in this community.",
                }))
                return

            saved_msg = await self.save_message(self.community_id, self.user, message_text)

            profile_pic = None
            if self.user.profile_picture:
                url = self.user.profile_picture.url
                profile_pic = url if url.startswith("http") else f"{self.base_url}{url}"

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "id": str(saved_msg.id),
                    "message": saved_msg.text,
                    "image": None,
                    "audio": None,
                    "sender": {
                        "id": self.user.id,
                        "username": self.user.username,
                        "first_name": self.user.first_name,
                        "last_name": self.user.last_name,
                        "profile_picture": profile_pic,
                    },
                    "created_at": str(saved_msg.created_at),
                },
            )
        except Exception as e:
            logger.error("community_ws_receive_error", error=str(e), exc_info=True)
            await self.send(text_data=json.dumps({"type": "error", "message": "Failed to send message."}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_membership(self, community_id, user):
        try:
            return Membership.objects.get(community_id=community_id, user=user)
        except Membership.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, community_id, user, text):
        community = Community.objects.get(id=community_id)
        msg = CommunityMessage.objects.create(community=community, sender=user, text=text)
        community.save(update_fields=["updated_at"])
        return msg

    @database_sync_to_async
    def get_chat_history(self, community_id, base_url):
        def format_url(url):
            if not url:
                return None
            if url.startswith("http"):
                return url
            return f"{base_url}{url}"

        messages = list(
            CommunityMessage.objects.filter(community_id=community_id)
            .select_related("sender")
            .order_by("-created_at")[:50]
        )
        messages.reverse()

        return [
            {
                "id": str(m.id),
                "message": m.text,
                "image": format_url(m.image.url) if m.image else None,
                "audio": format_url(m.audio.url) if m.audio else None,
                "sender": {
                    "id": m.sender.id,
                    "username": m.sender.username,
                    "first_name": m.sender.first_name,
                    "last_name": m.sender.last_name,
                    "profile_picture": format_url(m.sender.profile_picture.url) if m.sender.profile_picture else None,
                },
                "created_at": str(m.created_at),
            }
            for m in messages
        ]