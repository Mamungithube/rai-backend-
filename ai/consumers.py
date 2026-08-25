import json
import structlog
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from .tasks import generate_ai_response
from .services import AIService

logger = structlog.get_logger(__name__)

MAX_MESSAGE_LENGTH = 50000


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            logger.warning("ws_connect_rejected_anonymous")
            await self.close(code=4001)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"].get(
            "conversation_id")

        if self.conversation_id:
            self.room_group_name = f"chat_{self.conversation_id}"

            exists = await self.check_conversation_exists(self.conversation_id, self.user)
            if not exists:
                logger.warning(
                    "ws_connect_conversation_not_found",
                    user_id=self.user.id,
                    conversation_id=self.conversation_id,
                )
                await self.close(code=4004)
                return

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            history = await self.get_chat_history(self.conversation_id)
            await self.send_json({
                "type": "chat_history",
                "conversation_id": self.conversation_id,
                "messages": history,
            })
        else:
            await self.accept()

        logger.info("ws_connected", user_id=self.user.id,
                    conversation_id=self.conversation_id)

    async def disconnect(self, close_code):
        if hasattr(self, "conversation_id") and self.conversation_id:
            has_processing = await self.check_processing_messages(self.conversation_id)
            if not has_processing:
                lock_key = f"ai_processing_lock:{self.conversation_id}:{self.user.id}"
                await database_sync_to_async(cache.delete)(lock_key)

        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        logger.info("ws_disconnected", user_id=getattr(
            self.user, "id", None), code=close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as e:
            logger.warning("ws_invalid_json", error=str(e))
            await self.send_json({"type": "error", "code": "invalid_json", "message": "Invalid JSON payload."})
            return

        try:
            message_text = data.get("message", "").strip()
            image_id = data.get("image_id")

            if not message_text and not image_id:
                return

            if message_text and len(message_text) > MAX_MESSAGE_LENGTH:
                await self.send_json({
                    "type": "error",
                    "code": "message_too_long",
                    "message": f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.",
                })
                return

            if not self.conversation_id:
                conversation = await self.create_new_conversation(self.user)
                self.conversation_id = str(conversation.id)
                self.room_group_name = f"chat_{self.conversation_id}"
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)

                await self.send_json({
                    "type": "conversation_created",
                    "conversation_id": self.conversation_id,
                })

            lock_key = f"ai_processing_lock:{self.conversation_id}:{self.user.id}"
            has_processing = await self.check_processing_messages(self.conversation_id)
            if not has_processing:
                await database_sync_to_async(cache.delete)(lock_key)

            if not await self.acquire_lock(lock_key, 240):
                await self.send_json({
                    "type": "error",
                    "code": "ai_busy",
                    "message": "AI is still thinking. Please wait.",
                })
                return

            is_new_chat = (await self.get_message_count(self.conversation_id, image_id)) == 0

            try:
                msg = await self.save_message(self.conversation_id, message_text, "user", image_id)
            except Exception as e:
                logger.error("ws_save_message_failed",
                             error=str(e), exc_info=True)
                await database_sync_to_async(cache.delete)(lock_key)
                await self.send_json({
                    "type": "error",
                    "code": "save_failed",
                    "message": "Failed to save your message. Please try again.",
                })
                return

            from django.conf import settings

            def format_url(url):
                if not url:
                    return None
                if url.startswith("http"):
                    return url
                return f"{settings.SERVER_BASE_URL}{url}"

            await self.send_json({
                "type": "new_message",
                "conversation_id": self.conversation_id,
                "message": {
                    "id": msg.id,
                    "text": msg.text,
                    "sender": msg.sender,
                    "is_ai": False,
                    "status": msg.status,
                    "image_id": image_id,
                    "image_url": format_url(msg.image.url) if msg.image else None,
                    "created_at": str(msg.created_at),
                },
            })

            try:
                generate_ai_response.delay(
                    str(self.conversation_id),
                    message_text,
                    self.user.id,
                    is_new_chat,
                )
                logger.info(
                    "celery_task_dispatched",
                    user_id=self.user.id,
                    conversation_id=self.conversation_id,
                )
            except Exception as e:
                logger.error("celery_dispatch_failed",
                             error=str(e), exc_info=True)
                await database_sync_to_async(cache.delete)(lock_key)
                await self.send_json({
                    "type": "error",
                    "code": "ai_unavailable",
                    "message": "AI service is temporarily unavailable. Your message was saved — please try again in a moment.",
                })

        except Exception as e:
            logger.error("ws_receive_error", error=str(e), exc_info=True)
            await self.send_json({"type": "error", "code": "server_error", "message": "A server error occurred."})

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

    async def message_update(self, event):
        await self.send_json({
            "type": "message_update",
            "conversation_id": event["conversation_id"],
            "message": event["message"],
        })

    async def chat_title_update(self, event):
        await self.send_json({"type": "title_updated", "title": event["title"]})

    async def chat_error(self, event):
        await self.send_json({"type": "error", "message": event["message"]})

    @database_sync_to_async
    def acquire_lock(self, key, timeout):
        return cache.add(key, "true", timeout)

    @database_sync_to_async
    def check_processing_messages(self, conv_id):
        from .models import Message
        return Message.objects.filter(conversation_id=conv_id, status="processing").exists()

    @database_sync_to_async
    def check_conversation_exists(self, conv_id, user):
        from .models import Conversation
        return Conversation.objects.filter(id=conv_id, user=user, is_active=True).exists()

    @database_sync_to_async
    def create_new_conversation(self, user):
        return AIService.create_conversation(user)

    @database_sync_to_async
    def save_message(self, conv_id, text, sender, image_id):
        from .models import Message
        if image_id:
            try:
                msg = Message.objects.get(id=image_id, conversation_id=conv_id)
            except Message.DoesNotExist:
                raise ValueError(
                    f"Image message {image_id} not found in conversation {conv_id}")
            msg.text = text
            msg.status = "completed"
            msg.save(update_fields=["text", "status"])
            return msg
        else:
            return Message.objects.create(
                conversation_id=conv_id,
                text=text,
                sender=sender,
                status="completed",
            )

    @database_sync_to_async
    def get_message_count(self, conv_id, exclude_id=None):
        from .models import Message
        qs = Message.objects.filter(conversation_id=conv_id)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        return qs.count()

    @database_sync_to_async
    def get_chat_history(self, conv_id):
        from .models import Message
        from django.conf import settings

        def format_url(url):
            if not url:
                return None
            if url.startswith("http"):
                return url
            return f"{settings.SERVER_BASE_URL}{url}"

        messages = Message.objects.filter(
            conversation_id=conv_id).order_by("created_at")
        return [
            {
                "id": m.id,
                "text": m.text,
                "sender": m.sender,
                "is_ai": m.sender == "ai",
                "status": m.status,
                "image_id": m.id if m.image else None,
                "image_url": format_url(m.image.url) if m.image else None,
                "created_at": str(m.created_at),
            }
            for m in messages
        ]
