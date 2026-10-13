import structlog
import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import Match, Pick, SportCategory
from .utils import calculate_metrics, calculate_no_vig_probs, american_to_decimal

logger = structlog.get_logger(__name__)

FUTURES_SPORT_KEYS = [
    'americanfootball_nfl_super_bowl_winner',
    'basketball_nba_championship_winner',
    'soccer_epl_winner',
    'baseball_mlb_world_series_winner',
    'icehockey_nhl_championship_winner',
    'soccer_uefa_champs_league_winner',
]


@shared_task
def sync_odds_data():
    logger.info("sync_odds_started")
    api_key = getattr(settings, 'THE_ODDS_API_KEY', '')
    if not api_key:
        logger.error("odds_api_key_missing")
        return

    bookies = "pinnacle,draftkings,fanduel,betmgm,willhill_us,pointsbetus,betrivers,caesars"
    url = f"https://api.the-odds-api.com/v4/sports/upcoming/odds/?regions=us&markets=h2h&oddsFormat=american&bookmakers={bookies}&apiKey={api_key}"

    picks_created = 0
    picks_updated = 0

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
                defaults={
                    'start_time': game['commence_time'],
                    'is_active': True,
                    'is_futures': False,
                }
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

                            _, created = Pick.objects.update_or_create(
                                match=match,
                                team_selected=team_name,
                                defaults={
                                    'pick_type': 'Moneyline',
                                    'is_futures': False,
                                    'odds_american': odds,
                                    'confidence_percentage': metrics['confidence'],
                                    'edge_percentage': metrics['edge'],
                                    'ev_percentage': metrics['ev']
                                }
                            )
                            if created:
                                picks_created += 1
                            else:
                                picks_updated += 1

        if not Pick.objects.filter(is_pick_of_the_day=True).exists():
            top_pick = Pick.objects.order_by('-ev_percentage').first()
            if top_pick:
                top_pick.is_pick_of_the_day = True
                top_pick.save(update_fields=['is_pick_of_the_day'])

        logger.info(
            "sync_odds_completed",
            picks_created=picks_created,
            picks_updated=picks_updated,
            total_picks=picks_created + picks_updated,
        )
    except Exception as e:
        logger.error(
            "sync_odds_failed",
            error=str(e),
            picks_created=picks_created,
            picks_updated=picks_updated,
            exc_info=True,
        )


@shared_task
def sync_futures_odds():
    logger.info("sync_futures_odds_started")
    api_key = getattr(settings, 'THE_ODDS_API_KEY', '')
    if not api_key:
        logger.error("odds_api_key_missing")
        return

    picks_created = 0
    picks_updated = 0

    try:
        for sport_key in FUTURES_SPORT_KEYS:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?regions=us&markets=h2h&oddsFormat=american&apiKey={api_key}"
            try:
                response = requests.get(url, timeout=15)
                data = response.json()
            except Exception as req_err:
                logger.warning("futures_api_request_failed", sport_key=sport_key, error=str(req_err))
                continue

            if isinstance(data, dict) and "message" in data:
                logger.warning("futures_api_error_response", sport_key=sport_key, message=data["message"])
                continue

            if not isinstance(data, list):
                continue

            for event in data:
                sport, _ = SportCategory.objects.get_or_create(name=event.get('sport_key', sport_key))
                sport_title = event.get('sport_title') or sport_key.replace('_', ' ').title()
                home_team = (event.get('home_team') or sport_title)[:100]
                away_team = (event.get('away_team') or "Futures")[:100]
                commence_time = event.get('commence_time') or timezone.now()

                match, _ = Match.objects.get_or_create(
                    sport=sport,
                    home_team=home_team,
                    away_team=away_team,
                    defaults={
                        'start_time': commence_time,
                        'is_active': True,
                        'is_futures': True,
                    }
                )
                if not match.is_futures or not match.is_active:
                    match.is_futures = True
                    match.is_active = True
                    match.save(update_fields=['is_futures', 'is_active'])

                bookmakers = event.get('bookmakers', [])
                if not bookmakers:
                    continue

                # Calculate multi-outcome normalized probabilities across all bookmakers
                bookmaker_fair_probs = []
                for bookie in bookmakers:
                    for market in bookie.get('markets', []):
                        if market.get('key') in ['h2h', 'outrights']:
                            outcomes = market.get('outcomes', [])
                            if outcomes:
                                implied = {}
                                total_implied = 0.0
                                for out in outcomes:
                                    price = out.get('price')
                                    if price is not None:
                                        dec = american_to_decimal(price)
                                        if dec > 0:
                                            prob = 1.0 / dec
                                            implied[out['name']] = prob
                                            total_implied += prob
                                if total_implied > 0:
                                    norm_probs = {n: p / total_implied for n, p in implied.items()}
                                    bookmaker_fair_probs.append(norm_probs)

                # Average normalized market probabilities across bookmakers
                fair_market_probs = {}
                if bookmaker_fair_probs:
                    all_candidates = set()
                    for bp in bookmaker_fair_probs:
                        all_candidates.update(bp.keys())
                    for candidate in all_candidates:
                        probs = [bp[candidate] for bp in bookmaker_fair_probs if candidate in bp]
                        if probs:
                            fair_market_probs[candidate] = sum(probs) / len(probs)

                target_bookie = next((b for b in bookmakers if b.get('key') == 'draftkings'), bookmakers[0])
                for market in target_bookie.get('markets', []):
                    if market.get('key') in ['h2h', 'outrights']:
                        for outcome in market.get('outcomes', []):
                            team_name = outcome.get('name')
                            odds = outcome.get('price')
                            if not team_name or odds is None:
                                continue

                            fair_prob = fair_market_probs.get(team_name)
                            if fair_prob:
                                metrics = calculate_metrics(odds, fair_prob)
                            else:
                                dec = american_to_decimal(odds)
                                imp = (1.0 / dec) if dec > 0 else 0.0
                                metrics = {
                                    'confidence': int(imp * 100),
                                    'edge': 0.0,
                                    'ev': 0.0,
                                }

                            _, created = Pick.objects.update_or_create(
                                match=match,
                                team_selected=team_name[:100],
                                defaults={
                                    'pick_type': 'Futures',
                                    'is_futures': True,
                                    'odds_american': odds,
                                    'confidence_percentage': metrics['confidence'],
                                    'edge_percentage': metrics['edge'],
                                    'ev_percentage': metrics['ev'],
                                }
                            )
                            if created:
                                picks_created += 1
                            else:
                                picks_updated += 1

        logger.info(
            "sync_futures_odds_completed",
            picks_created=picks_created,
            picks_updated=picks_updated,
            total_picks=picks_created + picks_updated,
        )
    except Exception as e:
        logger.error(
            "sync_futures_odds_failed",
            error=str(e),
            picks_created=picks_created,
            picks_updated=picks_updated,
            exc_info=True,
        )