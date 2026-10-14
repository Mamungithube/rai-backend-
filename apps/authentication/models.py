from django.db import models
from django.db.models import F
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import RegexValidator
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken


class OTP(models.Model):
    identifier = models.CharField(max_length=255, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['identifier', 'created_at']),
            models.Index(fields=['identifier', 'is_verified']),
        ]
        ordering = ['-created_at']

    def is_valid(self):
        return (
            timezone.now() < self.created_at + timedelta(minutes=3)
            and self.attempts < 5
        )

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=['attempts'])

    @classmethod
    def cleanup_expired(cls):
        expiry_time = timezone.now() - timedelta(minutes=10)
        cls.objects.filter(created_at__lt=expiry_time).delete()

    def __repr__(self):
        return f"<OTP {self.identifier}: {self.code}>"


phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)


class User(AbstractUser):
    phone = models.CharField(
        validators=[phone_regex],
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )
    email = models.EmailField(
        max_length=200,
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        validators=[RegexValidator(
            regex=r'^[\w.@+-]+$',
            message='Username can only contain letters, numbers and @/./+/-/_ characters.'
        )]
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True, null=True, max_length=500)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_email_verified = models.BooleanField(default=False, db_index=True)
    is_phone_verified = models.BooleanField(default=False, db_index=True)
    is_admin = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['email', 'is_email_verified']),
            models.Index(fields=['phone', 'is_phone_verified']),
            models.Index(fields=['username', 'is_active']),
        ]

    def __str__(self):
        return self.username

    def __repr__(self):
        return f"<User {self.id}: {self.username}>"

    def is_user(self):
        return not self.is_admin

    def is_account_locked(self):
        if self.account_locked_until:
            if timezone.now() < self.account_locked_until:
                return True
            else:
                self.account_locked_until = None
                self.failed_login_attempts = 0
                self.save(update_fields=['account_locked_until', 'failed_login_attempts'])
        return False

    def record_failed_login(self):
        User.objects.filter(pk=self.pk).update(
            failed_login_attempts=F('failed_login_attempts') + 1,
            last_failed_login=timezone.now()
        )
        self.refresh_from_db(fields=['failed_login_attempts', 'last_failed_login'])

        if self.failed_login_attempts >= 5:
            User.objects.filter(pk=self.pk).update(
                account_locked_until=timezone.now() + timedelta(minutes=15)
            )
            self.refresh_from_db(fields=['account_locked_until'])

    def reset_failed_logins(self):
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.last_failed_login = None
            self.account_locked_until = None
            self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])

    @property
    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}