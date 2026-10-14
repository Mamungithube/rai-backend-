from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger("authentication")


class MultiFieldAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        username = username.lower().strip()

        try:
            user = User.objects.get(
                Q(username=username) |
                Q(email=username) |
                Q(phone=username)
            )
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            logger.error(f"Multiple users found for identifier: {username}")
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def user_can_authenticate(self, user):
        return getattr(user, 'is_active', False) is True