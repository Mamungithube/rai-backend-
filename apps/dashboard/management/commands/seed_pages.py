from django.core.management.base import BaseCommand
from dashboard.models import AppPage

PAGES_DATA = [
    {
        "slug": "about_us",
        "title": "About rai.",
        "content": (
            "rai. is an AI-powered sports assistant built to make sports betting smarter, clearer, and less stressful.\n\n"
            "We combine data, analytics, and artificial intelligence with a friendly tone and light humor to help users:\n"
            "• Save time researching games\n"
            "• Make confident decisions\n"
            "• Avoid emotional betting\n"
            "• Build smarter parlays\n"
            "• Our mission is simple:\n\n"
            "Help users bet smarter — not harder."
        )
    },
    {
        "slug": "privacy_policy",
        "title": "Privacy Policy",
        "content": (
            "Last updated: November 13, 2025\n\n"
            "At rai, your privacy matters. We are committed to protecting your personal information and being transparent about how data is used.\n\n"
            "What We Collect\n"
            "• Account information (name, email, username)\n"
            "• Usage data to improve AI predictions and app performance\n"
            "• Optional profile details such as bio and profile photo\n\n"
            "How We Use Your Data\n"
            "• To provide personalized picks and insights\n"
            "• To improve AI accuracy and user experience\n"
            "• To detect risky or emotional betting behavior\n"
            "• To manage subscriptions and account access\n\n"
            "We never sell your personal data. All information is stored securely and used only to enhance your experience with rai."
        )
    },
    {
        "slug": "terms_conditions",
        "title": "Terms & Conditions",
        "content": (
            "Effective Date: 1st December 2025\n\n"
            "By using rai, you agree to the following terms:\n"
            "• rai provides AI-generated insights for informational purposes only\n"
            "• All picks are suggestions, not guarantees\n"
            "• Users must be 18 years or older\n"
            "• You are responsible for your own betting decisions\n"
            "• rai is not affiliated with any sportsbook and does not place bets on your behalf\n\n"
            "Misuse of the app, abuse of features, or violation of rules may result in account suspension."
        )
    }
]


class Command(BaseCommand):
    help = "Seed or update default App Pages (About us, Privacy Policy, Terms & Conditions)"

    def handle(self, *args, **options):
        for item in PAGES_DATA:
            page, created = AppPage.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "content": item["content"]
                }
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} page: {page.title} ({page.slug})"))
