import os
import structlog
from django.conf import settings
from .models import Notification, FCMDevice
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = structlog.get_logger(__name__)

# Firebase Admin initialization (lazy / safe)
_firebase_initialized = False


def get_firebase_app():
    global _firebase_initialized
    if _firebase_initialized:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            # 1. Check if raw JSON string is provided in .env
            cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if cred_json:
                try:
                    import json
                    cred_json_str = cred_json.strip()
                    if cred_json_str.startswith('{'):
                        cred_dict = json.loads(cred_json_str)
                    else:
                        import base64
                        decoded = base64.b64decode(cred_json_str).decode('utf-8')
                        cred_dict = json.loads(decoded)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    logger.info("firebase_initialized_from_env_json")
                    _firebase_initialized = True
                    return True
                except Exception as json_err:
                    logger.warning("firebase_json_parse_failed", error=str(json_err))

            # 2. Check if file path is provided in .env
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("firebase_initialized_from_path", path=cred_path)
            else:
                # 3. Try default credentials or environment
                try:
                    firebase_admin.initialize_app()
                    logger.info("firebase_initialized_default")
                except Exception as init_err:
                    logger.warning("firebase_default_init_skipped", reason=str(init_err))
                    return False
        _firebase_initialized = True
        return True
    except ImportError:
        logger.debug("firebase_admin_not_installed")
        return False
    except Exception as e:
        logger.warning("firebase_init_failed", error=str(e))
        return False


def send_fcm_push(user, title, message, data=None):
    """
    Sends FCM Push Notification to all active devices registered to the user.
    """
    devices = list(FCMDevice.objects.filter(user=user, is_active=True))
    if not devices:
        return 0

    if not get_firebase_app():
        logger.debug("fcm_skipped_firebase_not_ready", user_id=user.id)
        return 0

    try:
        from firebase_admin import messaging

        tokens = [d.fcm_token for d in devices]
        str_data = {str(k): str(v) for k, v in (data or {}).items()}

        message_obj = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=message,
            ),
            data=str_data,
            tokens=tokens,
        )

        response = messaging.send_each_for_multicast(message_obj)
        logger.info(
            "fcm_multicast_sent",
            user_id=user.id,
            success_count=response.success_count,
            failure_count=response.failure_count
        )

        # Deactivate expired or invalid tokens
        if response.failure_count > 0:
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    err = resp.exception
                    # If unregistered or invalid token, mark inactive
                    if hasattr(err, 'code') and err.code in ['messaging/registration-token-not-registered', 'messaging/invalid-argument']:
                        devices[idx].is_active = False
                        devices[idx].save(update_fields=['is_active'])
                        logger.info("fcm_token_deactivated", token=devices[idx].fcm_token[:15])

        return response.success_count
    except Exception as e:
        logger.error("fcm_send_failed", error=str(e), user_id=user.id)
        return 0


def send_notification(user, title, message, notification_type='general', reference_id=None, extra_data=None):
    """
    Creates an in-app Notification record, broadcasts via WebSocket (if connected),
    and sends a Push Notification to the user's mobile devices via FCM.
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

        # 1. Broadcast via Channels group (WebSocket for real-time in-app updates)
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

        # 2. Dispatch FCM Push Notification to mobile devices
        try:
            send_fcm_push(user, title, message, extra_data)
        except Exception as fcm_err:
            logger.debug("notification_fcm_push_skipped", error=str(fcm_err))

        return notification
    except Exception as e:
        logger.error("failed_to_send_notification", error=str(e), user_id=getattr(user, 'id', None))
        return None
