def american_to_decimal(american_odds):
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def calculate_no_vig_probs(outcomes):
    if len(outcomes) != 2:
        return None
        
    decimal_odds = [american_to_decimal(o['price']) for o in outcomes]
    implied_probs = [1 / d for d in decimal_odds]
    total_implied_prob = sum(implied_probs)
    
    return {
        outcomes[i]['name']: implied_probs[i] / total_implied_prob 
        for i in range(len(outcomes))
    }

def calculate_metrics(target_odds, fair_probability):
    decimal_odds = american_to_decimal(target_odds)
    
    ev = (fair_probability * decimal_odds) - 1
    edge = ev
    confidence = int(fair_probability * 100)

    return {
        "confidence": confidence,
        "edge": round(edge * 100, 2),
        "ev": round(ev * 100, 2)
    }