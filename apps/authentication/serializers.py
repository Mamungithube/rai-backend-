import re
import uuid
import base64
from rest_framework import serializers
from .models import User, OTP
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from PIL import Image
from django.utils.crypto import constant_time_compare
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from django.core.files.base import ContentFile
from django.db.models import Q


ALLOWED_IMAGE_EXTENSIONS = ['jpeg', 'jpg', 'png', 'gif', 'webp']


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            if data.startswith('data:image'):
                try:
                    format, imgstr = data.split(';base64,')
                    ext = format.split('/')[-1].lower()
                    if ext not in ALLOWED_IMAGE_EXTENSIONS:
                        raise serializers.ValidationError(
                            f"Unsupported image format '{ext}'. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}."
                        )
                    data = ContentFile(
                        base64.b64decode(imgstr),
                        name=f"{uuid.uuid4().hex}.{ext}"
                    )
                except serializers.ValidationError:
                    raise
                except Exception:
                    raise serializers.ValidationError(
                        "Invalid base64 image data.")
            else:
                raise serializers.ValidationError(
                    "Expected a file upload or a base64 encoded image string."
                )
        return super().to_internal_value(data)


class PasswordValidator:
    @staticmethod
    def validate_password_strength(password):
        if (len(password) < 8 or
                not re.search(r"[A-Z]", password) or
                not re.search(r"[a-z]", password) or
                not re.search(r"\d", password) or
                not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)):
            raise serializers.ValidationError(
                "Password must be at least 8 characters long and include "
                "uppercase, lowercase, number, and special character."
            )


class SignupInitiateSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)

    def validate_identifier(self, value):
        value = value.strip()
        if '@' in value:
            value = value.lower()
            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid email format.")
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email already registered.")
        else:
            if not re.match(r'^\+?1?\d{9,15}$', value):
                raise serializers.ValidationError(
                    "Invalid phone number format.")
            if User.objects.filter(phone=value).exists():
                raise serializers.ValidationError("Phone already registered.")
        return value


class SignupVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate_identifier(self, value):
        value = value.strip()
        if '@' in value:
            value = value.lower()
        return value

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value


class SignupFinalizeSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        validators=[PasswordValidator.validate_password_strength]
    )
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    bio = serializers.CharField(
        required=False, allow_blank=True, max_length=500)
    date_of_birth = serializers.DateField(required=False)
    profile_picture = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'identifier', 'username', 'password',
            'first_name', 'last_name', 'bio',
            'date_of_birth', 'profile_picture'
        ]

    def validate_profile_picture(self, value):
        if value:
            if value.size > 50 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Image file size cannot exceed 50MB.")
            try:
                img = Image.open(value)
                img.verify()
                value.seek(0)
            except Exception:
                raise serializers.ValidationError("Invalid image file.")
        return value

    def validate_username(self, value):
        value = value.lower().strip()
        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must be at least 3 characters long.")
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers and @/./+/-/_ characters."
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    def validate(self, attrs):
        identifier = attrs.get('identifier')
        if '@' in identifier:
            identifier = identifier.lower().strip()
            if User.objects.filter(email=identifier).exists():
                raise serializers.ValidationError(
                    {"identifier": "This email is already registered."})
        else:
            identifier = identifier.strip()
            if User.objects.filter(phone=identifier).exists():
                raise serializers.ValidationError(
                    {"identifier": "This phone number is already registered."})
        attrs['identifier'] = identifier
        return attrs

    def create(self, validated_data):
        identifier = validated_data.pop('identifier')
        password = validated_data.pop('password')
        email = identifier if '@' in identifier else None
        phone = identifier if '@' not in identifier else None

        user = User.objects.create_user(
            username=validated_data['username'],
            email=email,
            phone=phone,
            password=password,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            bio=validated_data.get('bio', ''),
            date_of_birth=validated_data.get('date_of_birth', None),
            profile_picture=validated_data.get('profile_picture', None),
            is_active=True,
            is_email_verified=bool(email),
            is_phone_verified=bool(phone)
        )
        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get('username', '').lower().strip()
        attrs['username'] = username
        try:
            user = User.objects.get(Q(username=username) | Q(
                email=username) | Q(phone=username))
            if user.is_account_locked():
                raise serializers.ValidationError(
                    "Account is temporarily locked due to multiple failed login attempts."
                )
        except User.DoesNotExist:
            pass

        try:
            data = super().validate(attrs)
            user = self.user
            user.reset_failed_logins()
            return data
        except Exception as e:
            try:
                user = User.objects.get(Q(username=username) | Q(
                    email=username) | Q(phone=username))
                user.record_failed_login()
            except User.DoesNotExist:
                pass
            raise e


class ProfileSerializer(serializers.ModelSerializer):
    profile_picture = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone', 'profile_picture',
            'date_of_birth', 'bio', 'first_name', 'last_name'
        ]
        read_only_fields = ['username', 'email', 'phone']

    def update(self, instance, validated_data):
        profile_picture = validated_data.pop('profile_picture', None)
        if profile_picture is not None:
            instance.profile_picture = profile_picture

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.profile_picture:
            url = instance.profile_picture.url
            if not url.startswith('http'):
                request = self.context.get('request')
                if request:
                    url = request.build_absolute_uri(url)
                else:
                    url = f"{settings.SERVER_BASE_URL}{url}"
            data['profile_picture'] = url
        else:
            data['profile_picture'] = None
        return data

    def validate_profile_picture(self, value):
        if value:
            if value.size > 50 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Image file size cannot exceed 50MB.")
            try:
                img = Image.open(value)
                img.verify()
                value.seek(0)
            except Exception:
                raise serializers.ValidationError("Invalid image file.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)

    def validate_identifier(self, value):
        value = value.strip()
        if '@' in value:
            value = value.lower()
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    otp = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(
        validators=[PasswordValidator.validate_password_strength]
    )
    confirm_new_password = serializers.CharField()

    def validate_identifier(self, value):
        value = value.strip()
        if '@' in value:
            value = value.lower()
        return value

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError(
                {"confirm_new_password": "Passwords do not match."})

        identifier = attrs['identifier']
        try:
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone=identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"identifier": "No user found with this identifier."})

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        from .services import AuthService
        identifier = self.validated_data['identifier']
        otp = self.validated_data['otp']
        success, message, _ = AuthService.verify_otp(
            identifier, otp, self.context.get('request'))
        if not success:
            raise serializers.ValidationError({"otp": message})

        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        OTP.objects.filter(identifier=identifier).delete()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(
        validators=[PasswordValidator.validate_password_strength]
    )
    confirm_new_password = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError(
                {"confirm_new_password": "Passwords do not match."})
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError(
                {"old_password": "Wrong password."})
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from old password."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception:
            pass


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField()

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        suffix = f"_deleted_{uuid.uuid4().hex[:8]}"
        user.is_active = False
        user.username = f"{user.username}{suffix}"[:150]

        if user.email:
            user.email = f"{user.email}{suffix}"[:200]
        if user.phone:
            user.phone = f"{user.phone}{suffix}"[:20]
        user.save(update_fields=['is_active', 'username', 'email', 'phone'])


class ResendOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)

    def validate_identifier(self, value):
        value = value.strip()
        if '@' in value:
            value = value.lower()
            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid email format.")
        else:
            if not re.match(r'^\+?1?\d{9,15}$', value):
                raise serializers.ValidationError(
                    "Invalid phone number format.")
        return value


class EmailChangeInitiateSerializer(serializers.Serializer):
    new_email = serializers.EmailField(required=True)

    def validate_new_email(self, value):
        value = value.lower().strip()
        user = self.context['request'].user
        if value == user.email:
            raise serializers.ValidationError(
                "New email cannot be the same as the current email."
            )
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "This email is already in use by another account."
            )
        return value


class EmailChangeVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6, required=True)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value


class PhoneChangeInitiateSerializer(serializers.Serializer):
    new_phone = serializers.CharField(required=True)

    def validate_new_phone(self, value):
        value = value.strip()
        if not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError(
                "Invalid phone number format. Use '+999999999'."
            )
        user = self.context['request'].user
        if value == user.phone:
            raise serializers.ValidationError(
                "New phone number cannot be the same as the current phone number."
            )
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "This phone number is already in use by another account."
            )
        return value


class PhoneChangeVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6, required=True)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value
