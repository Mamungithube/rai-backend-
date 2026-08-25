import structlog
import requests
import secrets
from django.conf import settings
from django.core.mail import send_mail

logger = structlog.get_logger(__name__)


def generate_otp():
    return ''.join(secrets.choice('0123456789') for _ in range(6))


def send_otp_sms(phone, otp):
    url = f"{settings.INFOBIP_BASE_URL}/sms/3/messages"
    headers = {
        "Authorization": f"App {settings.INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    phone = phone.replace("+", "")

    payload = {
        "messages": [
            {
                "destinations": [{"to": phone}],
                "sender": settings.INFOBIP_SENDER_ID,
                "content": {
                    "text": f"Your verification code is {otp}. Expires in 3 minutes."
                }
            }
        ]
    }
    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=10)
        response_data = response.json() if response.content else {}
        response.raise_for_status()

        messages = response_data.get("messages", [])
        if messages:
            status = messages[0].get("status", {})
            group_name = status.get("groupName", "")
            if group_name in ("REJECTED", "UNDELIVERABLE"):
                logger.error("sms_rejected_by_infobip",
                             phone=phone, status=status)
                return False

        logger.info("sms_sent", phone=phone, infobip_response=response_data)
        return True
    except requests.exceptions.RequestException as e:
        err_msg = e.response.text if hasattr(
            e, 'response') and e.response is not None else str(e)
        logger.error("sms_failed", error=str(e), phone=phone, response=err_msg)
        return False

# def send_otp_email(email, otp):
#     url = f"{settings.INFOBIP_BASE_URL}/email/3/send"
#     headers = {
#         "Authorization": f"App {settings.INFOBIP_API_KEY}",
#         "Accept": "application/json"
#     }

#     payload = {
#         "from": (None, settings.DEFAULT_FROM_EMAIL),
#         "to": (None, email),
#         "subject": (None, "Your Verification Code"),
#         "text": (None, f"Your verification code is {otp}. Expires in 3 minutes."),
#     }

#     try:
#         response = requests.post(url, files=payload, headers=headers, timeout=10)
#         response_data = response.json() if response.content else {}
#         response.raise_for_status()

#         messages = response_data.get("messages", [])
#         if messages:
#             status = messages[0].get("status", {})
#             group_name = status.get("groupName", "")
#             if group_name in ("REJECTED", "UNDELIVERABLE"):
#                 logger.error("email_rejected_by_infobip", email=email, status=status)
#                 return False

#         logger.info("email_sent", email=email, infobip_response=response_data)
#         return True
#     except requests.exceptions.RequestException as e:
#         err_msg = e.response.text if hasattr(e, 'response') and e.response is not None else str(e)
#         logger.error("email_failed", error=str(e), email=email, response=err_msg)
#         return False


def send_otp_email(email, otp):
    try:
        send_mail(
            subject="Your Verification Code",
            message=f"Your verification code is {otp}. Expires in 3 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("email_sent", email=email)
        return True
    except Exception as e:
        logger.error("email_failed", error=str(e), email=email)
        return False


def send_otp(identifier, otp, method="email"):
    if method == "email":
        return send_otp_email(identifier, otp)
    elif method == "sms":
        return send_otp_sms(identifier, otp)
    return False
