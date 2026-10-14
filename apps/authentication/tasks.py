import logging
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def flush_expired_tokens_task(self):
    try:
        call_command("flushexpiredtokens")
        logger.info("Successfully flushed expired SimpleJWT tokens.")
        return "Tokens Flushed"
    except Exception as e:
        logger.error(f"Error flushing expired tokens: {e}")
        return str(e)

@shared_task
def cleanup_expired_otps_task():
    try:
        from authentication.models import OTP
        OTP.cleanup_expired()
        logger.info("Successfully cleaned up expired OTPs.")
        return "OTPs Cleaned"
    except Exception as e:
        logger.error(f"Error cleaning expired OTPs: {e}")
        return str(e)
