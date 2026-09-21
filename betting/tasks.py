import structlog
import requests
from celery import shared_task
from django.conf import settings
from .models import Match, Pick, SportCategory
from .utils import calculate_metrics, calculate_no_vig_probs

logger = structlog.get_logger(__name__)

@shared_task
def sync_odds_data():
    logger.info("sync_odds_started")
    api_key = getattr(settings, 'THE_ODDS_API_KEY', '')
    if not api_key:
        logger.error("odds_api_key_missing")
        return

    bookies = "pinnacle,draftkings,fanduel,betmgm,williamhill_us,pointsbetus,betrivers,caesars"
    url = f"https://api.the-odds-api.com/v4/sports/upcoming/odds/?regions=us&markets=h2h&oddsFormat=american&bookmakers={bookies}&apiKey={api_key}"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if isinstance(data, dict) and "message" in data:
            logger.error("odds_api_error_message", message=data["message"])
            return

        for game in data[:1000]:
            sport, _ = SportCategory.objects.get_or_create(name=game['sport_key'])
            match, _ = Match.objects.get_or_create(
                sport=sport,
                home_team=game['home_team'],
                away_team=game['away_team'],
                start_time=game['commence_time']
            )
            
            bookmakers = game.get('bookmakers', [])
            if not bookmakers:
                continue

            all_no_vig_probs = []
            for bookie in bookmakers:
                for market in bookie.get('markets', []):
                    if market['key'] == 'h2h':
                        probs = calculate_no_vig_probs(market['outcomes'])
                        if probs:
                            all_no_vig_probs.append(probs)

            if not all_no_vig_probs:
                continue

            teams = [game['home_team'], game['away_team']]
            fair_market_probs = {}
            for team in teams:
                team_probs = [p[team] for p in all_no_vig_probs if team in p]
                if team_probs:
                    fair_market_probs[team] = sum(team_probs) / len(team_probs)

            target_bookie = next((b for b in bookmakers if b['key'] == 'draftkings'), bookmakers[0])
            
            for market in target_bookie.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market.get('outcomes', []):
                        team_name = outcome['name']
                        if team_name in fair_market_probs:
                            odds = outcome['price']
                            metrics = calculate_metrics(odds, fair_market_probs[team_name])
                            
                            Pick.objects.update_or_create(
                                match=match,
                                team_selected=team_name,
                                defaults={
                                    'pick_type': 'Moneyline',
                                    'odds_american': odds,
                                    'confidence_percentage': metrics['confidence'],
                                    'edge_percentage': metrics['edge'],
                                    'ev_percentage': metrics['ev']
                                }
                            )
        if not Pick.objects.filter(is_pick_of_the_day=True).exists():
            top_pick = Pick.objects.order_by('-ev_percentage').first()
            if top_pick:
                top_pick.is_pick_of_the_day = True
                top_pick.save(update_fields=['is_pick_of_the_day'])

        logger.info("sync_odds_completed")
    except Exception as e:
        logger.error("sync_odds_failed", error=str(e), exc_info=True)