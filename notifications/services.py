import structlog
from .models import Notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = structlog.get_logger(__name__)


def send_notification(user, title, message, notification_type='general', reference_id=None, extra_data=None):
    """
    Creates and dispatches a notification to the specified user.
    """
    try:
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            data=extra_data or {}
        )

        # Broadcast via Channels group if user has a websocket open
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"user_{user.id}_notifications",
                    {
                        "type": "notification_message",
                        "data": {
                            "id": str(notification.id),
                            "title": notification.title,
                            "message": notification.message,
                            "notification_type": notification.notification_type,
                            "reference_id": notification.reference_id,
                            "data": notification.data,
                            "is_read": notification.is_read,
                            "created_at": notification.created_at.isoformat()
                        }
                    }
                )
        except Exception as ws_err:
            logger.debug("notification_ws_broadcast_skipped", error=str(ws_err))

        return notification
    except Exception as e:
        logger.error("failed_to_send_notification", error=str(e), user_id=getattr(user, 'id', None))
        return None
