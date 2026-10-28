import base64
import structlog
import tiktoken
from django.conf import settings
from django.db.models import Q
from .models import Message
from .prompts import extract_keywords, count_msg_tokens

logger = structlog.get_logger(__name__)


def generate_conversation_title(client, user_text):
    if not user_text:
        return None
    try:
        title_res = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Generate a short 3-word title based on the user prompt. Reply with only the title, no quotes.",
                },
                {"role": "user", "content": user_text[:100]},
            ],
            max_tokens=15,
        )
        return title_res.choices[0].message.content.strip().replace('"', "")
    except Exception as e:
        logger.warning("title_generation_failed", error=str(e))
        return None


def build_betting_context(user_text):
    picks_to_inject = []
    user_lower = (user_text or "").lower()
    in_depth_triggers = ['in-depth', 'in depth', 'give me the in-depth analysis', 'why they can win', 'what could stop them']
    futures_triggers = [
        'super bowl', 'superbowl', 'championship', 'champion', 'mvp', 
        'lombardi', 'division', 'conference', 'win total', 'playoff', 
        'outright', 'finals', 'world series', 'stanley cup'
    ]
    is_in_depth = any(t in user_lower for t in in_depth_triggers)
    is_futures = any(t in user_lower for t in futures_triggers)

    try:
        from betting.models import Pick

        keywords = extract_keywords(user_text)
        matched_picks = []
        if keywords:
            q_filter = Q()
            for kw in keywords:
                q_filter |= (
                    Q(match__home_team__icontains=kw) |
                    Q(match__away_team__icontains=kw) |
                    Q(team_selected__icontains=kw) |
                    Q(match__sport__name__icontains=kw)
                )
            
            qs = (
                Pick.objects.select_related('match', 'match__sport')
                .prefetch_related('bookmaker_odds')
                .filter(match__is_active=True)
                .filter(q_filter)
            )
            if is_futures:
                qs = qs.order_by('-is_futures', '-ev_percentage')
            else:
                qs = qs.order_by('-ev_percentage', '-confidence_percentage')

            matched_picks = list(qs.distinct()[:15])

        if matched_picks:
            picks_to_inject = matched_picks
        else:
            base_qs = (
                Pick.objects.select_related('match', 'match__sport')
                .prefetch_related('bookmaker_odds')
                .filter(match__is_active=True)
            )
            if is_futures:
                base_qs = base_qs.filter(is_futures=True)
            picks_to_inject = list(base_qs.order_by('-created_at')[:15])
    except Exception as e:
        logger.warning("failed_to_fetch_betting_context", error=str(e), exc_info=True)
        picks_to_inject = []

    market_context = "REAL-TIME MARKET CONTEXT (Live Betting Odds & Market Consensus):\n"
    if picks_to_inject:
        for p in picks_to_inject:
            p_is_futures = getattr(p, 'is_futures', False) or p.pick_type in ['Futures', 'Outright Winner']
            sport_name = p.match.sport.name if p.match and p.match.sport else 'Sports'
            lines_str = ""
            if hasattr(p, 'bookmaker_odds'):
                bmo_list = list(p.bookmaker_odds.all()[:4])
                if bmo_list:
                    lines_str = " | Lines: " + ", ".join(f"{bmo.bookmaker_name}: {bmo.odds_american:+d}" for bmo in bmo_list)

            if p_is_futures:
                event_title = p.match.home_team if p.match else 'Outright'
                market_context += (
                    f"- [FUTURES] [{sport_name}] Event: {event_title} | Outcome: {p.team_selected} | "
                    f"Odds: {p.odds_american} | Edge: {p.edge_percentage}% | EV: {p.ev_percentage}% | "
                    f"Confidence: {p.confidence_percentage}%{lines_str}\n"
                )
            else:
                market_context += (
                    f"- [{sport_name}] {p.match.home_team} vs {p.match.away_team} | "
                    f"Pick: {p.team_selected} ({p.pick_type}) | Odds: {p.odds_american} | "
                    f"Edge: {p.edge_percentage}% | EV: {p.ev_percentage}% | "
                    f"Confidence: {p.confidence_percentage}%{lines_str}\n"
                )
    else:
        market_context += "No specific database picks found for this query.\n"

    instructions = [
        "- Use the above live market consensus data when addressing relevant picks, matchups, or odds."
    ]
    if is_in_depth:
        instructions.append("- USER INTENT: IN-DEPTH ANALYSIS. Deliver the Tier 2 deep dive formatted exactly as '# THE IN-DEPTH ANALYSIS' with 'Why They Can Win' and 'What Could Stop Them' (identifying rival contenders with win-loss records and stats).")
    elif is_futures:
        instructions.append("- USER INTENT: FUTURES BETTING QUERY. Deliver the Tier 1 concise prediction with realistic futures confidence (10%-28%), key Injuries, Current Lines, and the '[GIVE ME THE IN-DEPTH ANALYSIS]' button at the end.")
    else:
        instructions.append("- Standard single game or prop query: follow regular matchup structure.")

    instructions_str = "\n".join(instructions)

    logger.info(
        "betting_context_injected",
        query=user_text,
        is_futures=is_futures,
        is_in_depth=is_in_depth,
        picks_injected_count=len(picks_to_inject),
    )

    return {
        "role": "system",
        "content": (
            f"{market_context}\n"
            f"CONTEXT USAGE INSTRUCTIONS:\n"
            f"{instructions_str}\n"
            "- If specific odds or matchup data is not listed above, follow the MISSING DATA PROTOCOL: "
            "provide expert analysis using contemporary current season context, never citing years-old rosters as current."
        ),
    }


def build_message_history(conversation_id, exclude_msg_id=None):
    query = Message.objects.filter(conversation_id=conversation_id)
    if exclude_msg_id:
        query = query.exclude(id=exclude_msg_id)

    recent_msgs = list(query.order_by("created_at"))

    hist_list = []
    for msg in recent_msgs:
        role = "assistant" if msg.sender == "ai" else "user"
        content = []
        if msg.text:
            content.append({"type": "text", "text": msg.text})

        if msg.image:
            try:
                with msg.image.open("rb") as img_file:
                    encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
                ext = msg.image.name.split(".")[-1].lower() if "." in msg.image.name else "jpeg"
                mime_type = f"image/{ext}" if ext in ["jpeg", "png", "webp", "gif"] else "image/jpeg"
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{encoded_string}"},
                })
            except Exception as e:
                logger.error(
                    "vision_image_fetch_failed",
                    error=str(e),
                    image_id=msg.id,
                    exc_info=True,
                )

        if content:
            if len(content) == 1 and content[0]["type"] == "text":
                hist_list.append({"role": role, "content": content[0]["text"]})
            else:
                hist_list.append({"role": role, "content": content})

    return hist_list


def truncate_message_history(hist_list, system_messages, max_tokens=120000):
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logger.warning("tiktoken_encoding_failed", error=str(e))
        encoding = None

    sys_tokens = sum(count_msg_tokens(m, encoding) for m in system_messages)

    if len(hist_list) > 6:
        first_msgs = hist_list[:2]
        middle_msgs = hist_list[2:-4]
        last_msgs = hist_list[-4:]

        first_tokens = sum(count_msg_tokens(m, encoding) for m in first_msgs)
        last_tokens = sum(count_msg_tokens(m, encoding) for m in last_msgs)
        middle_tokens = sum(count_msg_tokens(m, encoding) for m in middle_msgs)
        total_tokens = sys_tokens + first_tokens + middle_tokens + last_tokens

        while middle_msgs and total_tokens > max_tokens:
            dropped = middle_msgs.pop(0)
            total_tokens -= count_msg_tokens(dropped, encoding)

        final_hist = first_msgs + middle_msgs + last_msgs
    else:
        final_hist = hist_list

    messages_payload = system_messages + final_hist
    total_tokens = sum(count_msg_tokens(m, encoding) for m in messages_payload)
    return messages_payload, total_tokens
