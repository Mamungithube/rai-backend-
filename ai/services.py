import structlog
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Conversation, Message

logger = structlog.get_logger(__name__)


class AIService:

    @staticmethod
    def get_user_conversations(user):
        return Conversation.objects.filter(
            user=user,
            is_active=True
        ).order_by('-updated_at')

    @staticmethod
    def get_messages(user, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, user=user, is_active=True)
        return Message.objects.filter(conversation=conversation).order_by('created_at')

    @staticmethod
    def create_conversation(user, title="New Chat"):
        conversation = Conversation.objects.create(user=user, title=title)
        logger.info("conversation_created", user_id=user.id, conversation_id=str(conversation.id))
        return conversation

    @staticmethod
    def delete_conversation(user, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, user=user, is_active=True)
        conversation.is_active = False
        conversation.save(update_fields=['is_active'])
        logger.info("conversation_deleted", user_id=user.id, conversation_id=str(conversation.id))
        return True

    @staticmethod
    def save_message(conversation_id, text, sender, image_id=None):
        with transaction.atomic():
            if image_id:
                msg = Message.objects.get(id=image_id, conversation_id=conversation_id)
                msg.text = text
                msg.save(update_fields=['text'])
            else:
                Message.objects.create(
                    conversation_id=conversation_id,
                    text=text,
                    sender=sender,
                )

            Conversation.objects.filter(id=conversation_id).update(updated_at=timezone.now())
            return True