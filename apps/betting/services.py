import structlog
from django.db import transaction
from .models import UserParlay, Pick
from .utils import calculate_metrics

logger = structlog.get_logger(__name__)


class BettingService:
    @staticmethod
    def create_parlay(user, pick_ids):
        picks = Pick.objects.filter(id__in=pick_ids)
        if not picks.exists():
            return None, "No valid picks found."

        with transaction.atomic():
            parlay = UserParlay.objects.create(user=user)
            parlay.picks.set(picks)
            avg_conf = sum(
                p.confidence_percentage for p in picks) / picks.count()
            parlay.overall_confidence = int(avg_conf)
            parlay.total_odds = BettingService._combine_american_odds(picks)
            parlay.save(update_fields=['overall_confidence', 'total_odds'])

        logger.info("parlay_created", user_id=user.id,
                    parlay_id=str(parlay.id))
        return parlay, "Parlay built successfully."

    @staticmethod
    def _combine_american_odds(picks):
        from .utils import american_to_decimal
        combined_decimal = 1.0
        for p in picks:
            combined_decimal *= american_to_decimal(p.odds_american)

        # convert combined decimal odds back to American format
        if combined_decimal >= 2.0:
            return int((combined_decimal - 1) * 100)
        else:
            return int(-100 / (combined_decimal - 1))
