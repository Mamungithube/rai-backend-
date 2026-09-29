from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from notifications.models import Notification, FCMDevice

User = get_user_model()


class NotificationAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="notifyuser",
            email="notify@example.com",
            password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_notifications(self):
        Notification.objects.create(
            user=self.user,
            title="Test Alert",
            message="This is a test notification."
        )
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_unread_count(self):
        Notification.objects.create(
            user=self.user,
            title="Unread Alert",
            message="Unread notification message",
            is_read=False
        )
        response = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 1)

    def test_register_and_remove_fcm_token(self):
        # Register FCM token
        reg_response = self.client.post("/api/notifications/fcm-token/", {
            "fcm_token": "test_token_abc_123",
            "device_type": "android"
        }, format="json")
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FCMDevice.objects.filter(fcm_token="test_token_abc_123", is_active=True).exists())

        # Remove FCM token
        rem_response = self.client.post("/api/notifications/fcm-token/remove/", {
            "fcm_token": "test_token_abc_123"
        }, format="json")
        self.assertEqual(rem_response.status_code, status.HTTP_200_OK)
        self.assertFalse(FCMDevice.objects.get(fcm_token="test_token_abc_123").is_active)
