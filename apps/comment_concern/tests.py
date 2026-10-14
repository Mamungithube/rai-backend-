from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from comment_concern.models import CommentConcern

User = get_user_model()


class CommentConcernAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123"
        )
        self.admin = User.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            password="adminpassword123"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_comment_concern(self):
        """Test submitting a new comment & concern"""
        data = {
            "message": "The parlay builder is awesome, but I think a risk warning before placing high-leg parlays would really help users."
        }
        response = self.client.post("/api/comments/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("ticket_code", response.data)
        self.assertEqual(len(response.data["ticket_code"]), 8)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["status_display"], "Pending")
        self.assertIsNotNone(response.data["formatted_date"])

    def test_list_user_comments(self):
        """Test listing comments for authenticated user"""
        CommentConcern.objects.create(
            user=self.user,
            message="First test concern message"
        )
        CommentConcern.objects.create(
            user=self.user,
            message="Second test concern message"
        )
        response = self.client.get("/api/comments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_get_single_comment_detail(self):
        """Test retrieving a single comment & concern detail"""
        comment = CommentConcern.objects.create(
            user=self.user,
            message="Detail test message"
        )
        response = self.client.get(f"/api/comments/{comment.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ticket_code"], comment.ticket_code)

    def test_empty_message_validation(self):
        """Test validation when submitting empty message"""
        response = self.client.post("/api/comments/", {"message": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
