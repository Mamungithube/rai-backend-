from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from dashboard.models import AppPage


class AppPagesAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.about = AppPage.objects.create(
            slug="about_us",
            title="About rai.",
            content="rai. is an AI-powered sports assistant..."
        )
        self.privacy = AppPage.objects.create(
            slug="privacy_policy",
            title="Privacy Policy",
            content="At rai, your privacy matters..."
        )
        self.terms = AppPage.objects.create(
            slug="terms_conditions",
            title="Terms & Conditions",
            content="By using rai, you agree to the following terms..."
        )

    def test_get_about_us_public(self):
        """Test public access to about_us page without token"""
        response = self.client.get("/api/pages/about_us/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "about_us")
        self.assertEqual(response.data["title"], "About rai.")

    def test_get_privacy_policy_public(self):
        """Test public access to privacy_policy page without token"""
        response = self.client.get("/api/pages/privacy_policy/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "privacy_policy")
        self.assertIn("privacy", response.data["content"].lower())

    def test_get_terms_conditions_public(self):
        """Test public access to terms_conditions page without token"""
        response = self.client.get("/api/pages/terms_conditions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "terms_conditions")

    def test_list_all_pages(self):
        """Test listing all pages"""
        response = self.client.get("/api/pages/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)
