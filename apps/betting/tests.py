import uuid
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import SportCategory, Match, Pick, SavedPick, UserParlay

User = get_user_model()


class BettingAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="StrongPassword123!"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.sport = SportCategory.objects.create(name="NFL")
        self.match = Match.objects.create(
            sport=self.sport,
            home_team="Bengals",
            away_team="Browns",
            start_time=timezone.now(),
            is_active=True
        )
        self.pick = Pick.objects.create(
            match=self.match,
            team_selected="Bengals",
            pick_type="Spread",
            point_spread=5.5,
            odds_american=135,
            confidence_percentage=80,
            is_pick_of_the_day=True,
            breakdown_text="Test analysis"
        )

    def test_daily_picks_endpoint(self):
        response = self.client.get('/api/betting/daily_picks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_pick_of_the_day_endpoint(self):
        response = self.client.get('/api/betting/pick_of_the_day/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(p['id'] == str(self.pick.id) for p in response.data))

    def test_toggle_save_pick(self):
        # Save pick
        response = self.client.post(f'/api/betting/{self.pick.id}/toggle_save/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'saved')
        self.assertTrue(SavedPick.objects.filter(user=self.user, pick=self.pick).exists())

        # Unsave pick
        response_unsave = self.client.post(f'/api/betting/{self.pick.id}/toggle_save/')
        self.assertEqual(response_unsave.status_code, status.HTTP_200_OK)
        self.assertEqual(response_unsave.data.get('status'), 'removed')
        self.assertFalse(SavedPick.objects.filter(user=self.user, pick=self.pick).exists())

    def test_toggle_save_invalid_uuid(self):
        response = self.client.post('/api/betting/not-a-valid-uuid/toggle_save/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_build_parlay(self):
        response = self.client.post('/api/betting/build_parlay/', {
            'pick_ids': [str(self.pick.id)]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('parlay_id', response.data)
