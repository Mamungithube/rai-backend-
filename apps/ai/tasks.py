import structlog
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
from .models import Conversation, Message
from .prompts import SYSTEM_PROMPT, validate_input
from .context_builder import (
    generate_conversation_title,
    build_betting_context,
    build_message_history,
    truncate_message_history,
)

logger = structlog.get_logger(__name__)


def send_ws_message(conversation_id, message_data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation_id}",
        {
            "type": "message_update",
            "conversation_id": str(conversation_id),
            "message": message_data,
        },
    )


def _fail_ai_message(ai_msg, conversation_id, text="System Error. AI is currently unavailable."):
    ai_msg.status = "failed"
    ai_msg.text = text
    ai_msg.save(update_fields=["status", "text"])
    send_ws_message(conversation_id, {
        "id": ai_msg.id,
        "text": ai_msg.text,
        "sender": "ai",
        "is_ai": True,
        "status": "failed",
        "created_at": str(ai_msg.created_at),
    })


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def generate_ai_response(self, conversation_id, user_text, user_id, is_new_chat=False):
    channel_layer = get_channel_layer()
    group_name = f"chat_{conversation_id}"
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30.0)
    ai_msg = None

    logger.info(
        "ai_task_started",
        conversation_id=conversation_id,
        user_id=user_id,
        attempt=self.request.retries + 1,
    )

    try:
        if not validate_input(user_text):
            logger.warning(
                "prompt_injection_detected",
                user_id=user_id,
                conversation_id=conversation_id,
            )
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "chat_error",
                    "message": "I cannot comply with that request due to safety guidelines.",
                },
            )
            return

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            logger.error(
                "ai_task_conversation_not_found",
                conversation_id=conversation_id,
            )
            return

        ai_msg = Message.objects.create(
            conversation=conversation,
            sender="ai",
            text="",
            status="processing",
        )

        send_ws_message(conversation_id, {
            "id": ai_msg.id,
            "text": "",
            "sender": "ai",
            "is_ai": True,
            "status": "processing",
            "created_at": str(ai_msg.created_at),
        })

        # Generate conversation title for new chats
        if is_new_chat and user_text:
            title = generate_conversation_title(client, user_text)
            if title:
                conversation.title = title[:100]
                conversation.save(update_fields=["title", "updated_at"])
                async_to_sync(channel_layer.group_send)(
                    group_name, {"type": "chat_title_update", "title": title}
                )

        # Build context & history payload
        system_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        betting_context_msg = build_betting_context(user_text)
        if betting_context_msg:
            system_messages.append(betting_context_msg)

        hist_list = build_message_history(conversation_id, exclude_msg_id=ai_msg.id)
        messages_payload, total_tokens = truncate_message_history(hist_list, system_messages)

        logger.info(
            "ai_prompt_constructed",
            total_tokens=total_tokens,
            system_prompt_length=len(SYSTEM_PROMPT),
        )

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages_payload,
            max_tokens=1000,
        )

        ai_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        ai_msg.text = ai_text
        ai_msg.token_count = tokens_used
        ai_msg.status = "completed"
        ai_msg.save(update_fields=["text", "token_count", "status"])

        Conversation.objects.filter(id=conversation_id).update(
            total_tokens_used=F('total_tokens_used') + tokens_used
        )

        send_ws_message(conversation_id, {
            "id": ai_msg.id,
            "text": ai_text,
            "sender": "ai",
            "is_ai": True,
            "status": "completed",
            "created_at": str(ai_msg.created_at),
        })

        logger.info(
            "ai_task_completed",
            conversation_id=conversation_id,
            tokens_used=tokens_used,
        )

    except (RateLimitError, APITimeoutError, APIConnectionError) as e:
        logger.warning(
            "ai_transient_error_retrying",
            error=str(e),
            error_type=type(e).__name__,
            attempt=self.request.retries + 1,
            conversation_id=conversation_id,
        )

        if self.request.retries >= self.max_retries:
            if ai_msg:
                _fail_ai_message(
                    ai_msg,
                    conversation_id,
                    text="AI service is temporarily unavailable. Please try again.",
                )
            return

        if ai_msg:
            ai_msg.status = "processing"
            ai_msg.save(update_fields=["status"])

        raise self.retry(exc=e, countdown=15 * (self.request.retries + 1))

    except SoftTimeLimitExceeded:
        logger.error("ai_task_soft_timeout", conversation_id=conversation_id)
        if ai_msg:
            _fail_ai_message(
                ai_msg,
                conversation_id,
                text="Request timed out. Please try again.",
            )

    except Exception as e:
        logger.error(
            "ai_generation_failed",
            error=str(e),
            error_type=type(e).__name__,
            conversation_id=conversation_id,
            exc_info=True,
        )
        if ai_msg:
            _fail_ai_message(ai_msg, conversation_id)

    finally:
        cache.delete(f"ai_processing_lock:{conversation_id}:{user_id}")
