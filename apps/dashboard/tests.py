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


class AdminOverviewAPITestCase(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="testadmin",
            email="admin@test.com",
            password="AdminPassword123!",
            first_name="Peter John",
            last_name="White"
        )
        self.user1 = User.objects.create_user(
            username="trendify_co",
            email="test@gmail.com",
            password="UserPassword123!",
            first_name="Trendify",
            last_name="Co."
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_get_overview_authenticated_admin(self):
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        data = response.data["data"]

        # Check header
        self.assertIn("greeting", data["header"])
        self.assertIn("Peter John White", data["header"]["admin_name"])

        # Check user_overview
        self.assertEqual(data["user_overview"]["total_users"], 1)
        self.assertIn("cards", data["user_overview"])
        self.assertEqual(len(data["user_overview"]["cards"]), 4)

        # Check growth_overview
        self.assertIn("labels", data["growth_overview"])
        self.assertIn("data", data["growth_overview"])

        # Check subscriber/recent user list
        self.assertEqual(len(data["recent_users"]), 1)
        self.assertEqual(data["recent_users"][0]["username"], "trendify_co")

    def test_get_overview_growth_filters(self):
        for f in ["this_week", "this_month", "this_year"]:
            response = self.client.get(f"/api/dashboard/overview/?growth_filter={f}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["data"]["growth_overview"]["current_filter"], f)

