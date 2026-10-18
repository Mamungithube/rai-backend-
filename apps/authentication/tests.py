from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from .models import OTP

User = get_user_model()


class UserModelAndAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mamun",
            email="mamun@example.com",
            phone="+12345678901",
            password="StrongPassword123!"
        )
        self.client = APIClient()

    def test_user_creation_and_tokens(self):
        self.assertEqual(self.user.username, "mamun")
        self.assertEqual(self.user.email, "mamun@example.com")
        self.assertTrue(self.user.check_password("StrongPassword123!"))

        tokens = self.user.tokens
        self.assertIn("access", tokens)
        self.assertIn("refresh", tokens)

    def test_otp_validation_and_attempts(self):
        otp = OTP.objects.create(
            identifier="test@example.com",
            code="123456"
        )
        self.assertTrue(otp.is_valid())

        # Increment attempts up to max
        for _ in range(5):
            otp.increment_attempts()

        self.assertFalse(otp.is_valid())

    def test_otp_expiration(self):
        otp = OTP.objects.create(
            identifier="expire@example.com",
            code="654321"
        )
        OTP.objects.filter(pk=otp.pk).update(created_at=timezone.now() - timedelta(minutes=5))
        otp.refresh_from_db()
        self.assertFalse(otp.is_valid())

    def test_login_api_endpoint(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'mamun',
            'password': 'StrongPassword123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_api_invalid_credentials(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'mamun',
            'password': 'WrongPassword!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), 'mamun')
        self.assertEqual(response.data.get('email'), 'mamun@example.com')

    def test_update_profile_username_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch('/api/auth/profile/update/', {
            'username': 'new_mamun'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'new_mamun')

    def test_update_profile_username_duplicate_rejected(self):
        User.objects.create_user(username="existing_user", password="Password123!")
        self.client.force_authenticate(user=self.user)
        response = self.client.patch('/api/auth/profile/update/', {
            'username': 'existing_user'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_updated_username(self):
        # 1. Update username
        self.client.force_authenticate(user=self.user)
        self.client.patch('/api/auth/profile/update/', {'username': 'updated_mamun'}, format='json')

        # 2. Logout / unauthenticate
        self.client.logout()

        # 3. Old username login should fail
        res_old = self.client.post('/api/auth/login/', {
            'username': 'mamun',
            'password': 'StrongPassword123!'
        }, format='json')
        self.assertEqual(res_old.status_code, status.HTTP_401_UNAUTHORIZED)

        # 4. New username login should succeed
        res_new = self.client.post('/api/auth/login/', {
            'username': 'updated_mamun',
            'password': 'StrongPassword123!'
        }, format='json')
        self.assertEqual(res_new.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_new.data)

        # 5. Email login still works seamlessly
        res_email = self.client.post('/api/auth/login/', {
            'username': 'mamun@example.com',
            'password': 'StrongPassword123!'
        }, format='json')
        self.assertEqual(res_email.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_email.data)
