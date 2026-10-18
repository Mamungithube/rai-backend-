from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from betting.models import SportCategory, Match, Pick, BookmakerOdds
from community.models import Community, Membership

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds initial database for local development (pages, sport categories, demo picks, line shopping, communities, and admin)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("--- Starting Development Database Seeding ---"))

        # 1. Seed Pages
        self.stdout.write("1. Seeding App Pages...")
        try:
            call_command("seed_pages")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not run seed_pages: {e}"))

        # 2. Seed Sport Categories
        self.stdout.write("2. Seeding Sport Categories...")
        categories = ["NFL", "NBA", "MLB", "NHL", "Soccer", "UFC", "Tennis", "Boxing"]
        for cat in categories:
            obj, created = SportCategory.objects.get_or_create(name=cat)
            if created:
                self.stdout.write(f"   Created sport: {cat}")

        # 3. Seed Default Admin
        self.stdout.write("3. Checking Admin User...")
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username="admin",
                email="admin@rai.app",
                password="adminpassword123"
            )
            self.stdout.write(self.style.SUCCESS("   Created admin: admin / adminpassword123"))
        else:
            self.stdout.write("   Admin user already exists.")

        # 4. Seed Demo Match & Picks
        self.stdout.write("4. Seeding Demo Match & Picks...")
        nfl = SportCategory.objects.filter(name="NFL").first()
        if nfl:
            match, _ = Match.objects.get_or_create(
                sport=nfl,
                home_team="Cincinnati Bengals",
                away_team="Cleveland Browns",
                defaults={
                    "start_time": timezone.now() + timezone.timedelta(days=1),
                    "is_active": True
                }
            )

            # Pick 1: Dr. Jones Pick
            pick1, created1 = Pick.objects.get_or_create(
                match=match,
                team_selected="Cincinnati Bengals",
                pick_type="Spread",
                defaults={
                    "point_spread": 5.5,
                    "odds_american": 135,
                    "edge_percentage": 4.5,
                    "ev_percentage": 6.2,
                    "confidence_percentage": 80,
                    "breakdown_text": "I believe the Bengals will win by at least 6 with Joey B and Chase being healthy",
                    "is_pick_of_the_day": False,
                    "expert_name": "Dr. Jones",
                }
            )

            # Pick 2: Reese's Pick (Pick of the Day)
            pick2, created2 = Pick.objects.get_or_create(
                match=match,
                team_selected="Cincinnati Bengals",
                is_pick_of_the_day=True,
                defaults={
                    "pick_type": "Spread",
                    "point_spread": 5.5,
                    "odds_american": 135,
                    "edge_percentage": 8.23,
                    "ev_percentage": 9.83,
                    "confidence_percentage": 82,
                    "breakdown_text": "Reese's top spread pick for this NFL matchup.",
                    "expert_name": "Reese",
                }
            )

            # 5. Seed Line Shopping (BookmakerOdds)
            for p in [pick1, pick2]:
                bookie_lines = [
                    ("draftkings", "DraftKings", 135),
                    ("fanduel", "FanDuel", 130),
                    ("caesars", "Caesars Sportsbook", 140),
                    ("betmgm", "BetMGM", 132),
                ]
                for b_key, b_name, b_odds in bookie_lines:
                    BookmakerOdds.objects.get_or_create(
                        pick=p,
                        bookmaker_key=b_key,
                        defaults={
                            "bookmaker_name": b_name,
                            "odds_american": b_odds,
                            "point_spread": 5.5
                        }
                    )
            self.stdout.write(self.style.SUCCESS("   Seeded demo picks with multi-bookmaker odds (Line Shopping)."))

        # 6. Seed Demo Community
        self.stdout.write("6. Checking Demo Community...")
        comm, comm_created = Community.objects.get_or_create(
            name="VIP Betting Elite",
            defaults={
                "description": "High roller betting analysis, picks sharing and community discussions.",
                "is_private": False,
                "approval_required": False
            }
        )
        if admin_user:
            Membership.objects.get_or_create(
                community=comm,
                user=admin_user,
                defaults={"role": "admin"}
            )
            self.stdout.write(self.style.SUCCESS(f"   Admin attached to community: {comm.name}"))

        self.stdout.write(self.style.SUCCESS("--- Seeding Completed Successfully! ---"))

