import uuid
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.core.cache import cache
from .models import SportCategory, Match, Pick, SavedPick, UserParlay

User = get_user_model()


class BettingAPITests(TestCase):
    def setUp(self):
        cache.clear()
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

    def test_track_straight_bet(self):
        response = self.client.post(f'/api/betting/{self.pick.id}/track_straight_bet/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('status'), 'tracked')
        self.assertTrue(response.data.get('is_tracked'))

        # Check straight_bets list
        list_res = self.client.get('/api/betting/straight_bets/')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 1)

        # Toggle straight bet tracking
        toggle_res = self.client.post(f'/api/betting/{self.pick.id}/track_straight_bet/')
        self.assertEqual(toggle_res.status_code, status.HTTP_200_OK)
        self.assertEqual(toggle_res.data.get('status'), 'untracked')

    def test_line_shopping_endpoint(self):
        from .models import BookmakerOdds
        BookmakerOdds.objects.create(
            pick=self.pick,
            bookmaker_key="draftkings",
            bookmaker_name="DraftKings",
            odds_american=135,
            point_spread=5.5
        )
        BookmakerOdds.objects.create(
            pick=self.pick,
            bookmaker_key="caesars",
            bookmaker_name="Caesars Sportsbook",
            odds_american=140,
            point_spread=5.5
        )

        response = self.client.get(f'/api/betting/{self.pick.id}/line_shopping/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('lines', response.data)
        self.assertIn('best_line', response.data)
        self.assertEqual(len(response.data['lines']), 2)
        self.assertEqual(response.data['best_line']['bookmaker_name'], 'Caesars Sportsbook')

    def test_creators_picks_endpoint(self):
        self.pick.expert_name = "Dr. Jones"
        self.pick.save()

        response = self.client.get('/api/betting/creators_picks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        self.assertEqual(response.data[0]['expert_name'], 'Dr. Jones')

    def test_share_to_community(self):
        from community.models import Community, Membership
        comm = Community.objects.create(name="NFL Bettors")
        Membership.objects.create(community=comm, user=self.user, role="member")

        response = self.client.post(f'/api/betting/{self.pick.id}/share_to_community/', {
            'community_id': str(comm.id),
            'message': 'Bengals look like great value!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('status'), 'shared')

