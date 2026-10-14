from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from betting.models import SportCategory, Match, Pick

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds initial database for local development (pages, sport categories, demo picks, and admin)"

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
        if not User.objects.filter(is_superuser=True).exists():
            admin_user = User.objects.create_superuser(
                username="admin",
                email="admin@rai.app",
                password="adminpassword123"
            )
            self.stdout.write(self.style.SUCCESS("   Created admin: admin / adminpassword123"))
        else:
            self.stdout.write("   Admin user already exists.")

        # 4. Seed Demo Match & Pick
        self.stdout.write("4. Seeding Demo Match & Picks...")
        nfl = SportCategory.objects.filter(name="NFL").first()
        if nfl and not Match.objects.filter(home_team="Cincinnati Bengals").exists():
            match = Match.objects.create(
                sport=nfl,
                home_team="Cincinnati Bengals",
                away_team="Cleveland Browns",
                start_time=timezone.now() + timezone.timedelta(days=1),
                is_active=True
            )
            Pick.objects.create(
                match=match,
                team_selected="Cincinnati Bengals",
                pick_type="Spread",
                point_spread=5.5,
                odds_american=135,
                edge_percentage=4.5,
                ev_percentage=6.2,
                confidence_percentage=80,
                breakdown_text="Bengals are in strong form with healthy starters.",
                is_pick_of_the_day=True,
                expert_name="Dr. Jones",
            )
            self.stdout.write(self.style.SUCCESS("   Created demo match and Pick of the Day."))

        self.stdout.write(self.style.SUCCESS("--- Seeding Completed Successfully! ---"))
