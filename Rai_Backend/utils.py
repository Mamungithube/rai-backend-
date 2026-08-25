from django.conf import settings
from django.core.mail import send_mail
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def send_email(subject, message, recipient_list, html_message=None, retries=3):
    for attempt in range(retries):
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False,
                html_message=html_message
            )
            logger.info(f"Email sent successfully to {recipient_list}")
            return True
        except Exception as e:
            logger.error(f"Email sending attempt {attempt + 1} failed: {e}", exc_info=True)
            if attempt == retries - 1:
                return False
    return False


def api_response(message, data=None, success=True, status_code=status.HTTP_200_OK, extra=None):
    payload = {
        "success": success,
        "message": message,
        "data": data if data is not None else {}
    }

    if extra:
        payload.update(extra)

    return Response(payload, status=status_code)