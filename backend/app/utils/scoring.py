# backend/app/utils/scoring.py

from typing import Dict, Any, Optional


def _normalize_rating(rating: float) -> float:
    """Normalize rating to 0-1 scale (0-5 stars -> 0-1)"""
    return rating / 5 if rating else 0.0


def _normalize_popularity(votes: int) -> float:
    """Normalize popularity (votes/reviews) to 0-1 scale"""
    # Strong boost for 1000+ reviews, normalize to 0-1
    return min(1.0, votes / 1000) if votes else 0.0


def _cost_penalty(cost: int, activity_budget: float) -> float:
    """
    Cost penalty: λc·CostPenalty
    If cost beyond user's spending comfort → apply penalty.
    """
    if activity_budget == 0:
        return 0

    ratio = cost / activity_budget

    if ratio <= 0.3:
        return 0
    if ratio <= 0.6:
        return 0.05
    if ratio <= 1.0:
        return 0.15
    return 0.30  # too expensive


def _duration_fit(duration_min: float, energy: str) -> float:
    """
    DurationFit: How well the activity duration matches user's energy level.
    Returns 0-1 score where 1 = perfect fit.
    """
    if energy == "high":
        # High energy: prefer longer activities (2-4 hours)
        if duration_min < 60:
            return 0.3  # Too short
        elif duration_min <= 240:
            return min(1.0, 0.5 + (duration_min - 60) / 360)  # 60-240min is good
        else:
            return 1.0  # Very long activities are perfect
    elif energy == "low":
        # Low energy: prefer shorter activities (< 2 hours)
        if duration_min <= 90:
            return 1.0  # Perfect
        elif duration_min <= 180:
            return max(0.3, 1.0 - (duration_min - 90) / 180)  # 90-180min is acceptable
        else:
            return 0.2  # Too long
    else:  # medium
        # Medium energy: prefer moderate duration (1.5-3 hours)
        if duration_min < 60:
            return 0.4
        elif duration_min <= 180:
            return min(1.0, 0.6 + (duration_min - 60) / 240)  # 60-180min is good
        else:
            return max(0.5, 1.0 - (duration_min - 180) / 180)  # 180-240min is acceptable


def _travel_time_penalty(travel_time_min: float) -> float:
    """
    TravelTime penalty: λt·TravelTime
    Penalize based on travel time (in minutes).
    Returns penalty value (higher = worse).
    """
    if travel_time_min <= 0:
        return 0.0
    
    # Normalize: 0-30min = small penalty, 30-60min = medium, 60+ = large
    if travel_time_min <= 15:
        return travel_time_min / 15 * 0.05  # 0-0.05 penalty
    elif travel_time_min <= 30:
        return 0.05 + (travel_time_min - 15) / 15 * 0.10  # 0.05-0.15 penalty
    elif travel_time_min <= 60:
        return 0.15 + (travel_time_min - 30) / 30 * 0.20  # 0.15-0.35 penalty
    else:
        return 0.35 + min(0.30, (travel_time_min - 60) / 60 * 0.30)  # 0.35-0.65 max penalty


def score_activity_with_hybrid_algorithm(
    place: Dict[str, Any],
    preference_score: float,  # UserFit score
    energy: str,
    activity_budget: float,
    travel_time_min: Optional[float] = None,
) -> float:
    """
    Hybrid Scoring Algorithm:
    Score(a) = wr·Rating + wp·Popularity + wu·UserFit + wd·DurationFit – λt·TravelTime – λc·CostPenalty
    
    Where:
    - wr = weight for Rating (0.30)
    - wp = weight for Popularity (0.20)
    - wu = weight for UserFit (0.25)
    - wd = weight for DurationFit (0.15)
    - λt = penalty coefficient for TravelTime (0.10)
    - λc = penalty coefficient for CostPenalty (already calculated)
    """
    rating = place.get("rating", 0)
    votes = place.get("votes", 0)
    duration = place.get("duration_min", 90)
    cost = place.get("estimated_cost_vnd", 0)
    
    # Get travel time (default to 0 if not provided)
    travel_time = travel_time_min if travel_time_min is not None else place.get("travel_time_min", 0) or 0

    # Normalize components to 0-1 scale
    rating_norm = _normalize_rating(rating)  # wr·Rating
    popularity_norm = _normalize_popularity(votes)  # wp·Popularity
    user_fit = preference_score  # wu·UserFit (already 0-1)
    duration_fit = _duration_fit(duration, energy)  # wd·DurationFit
    
    # Penalties
    travel_penalty = _travel_time_penalty(travel_time)  # λt·TravelTime
    cost_penalty = _cost_penalty(cost, activity_budget)  # λc·CostPenalty

    # Hybrid Scoring Formula
    # Weights: wr=0.30, wp=0.20, wu=0.25, wd=0.15, λt=0.10
    score = (
        0.30 * rating_norm +           # wr·Rating
        0.20 * popularity_norm +       # wp·Popularity
        0.25 * user_fit +               # wu·UserFit
        0.15 * duration_fit -           # wd·DurationFit
        0.10 * travel_penalty -         # λt·TravelTime
        cost_penalty                    # λc·CostPenalty
    )

    return round(score, 4)


# Backward compatibility: keep old function name
def score_activity_with_algorithm1(
    place: Dict[str, Any],
    preference_score: float,
    energy: str,
    activity_budget: float,
) -> float:
    """
    Legacy function for backward compatibility.
    Now uses Hybrid Scoring Algorithm internally.
    """
    return score_activity_with_hybrid_algorithm(
        place=place,
        preference_score=preference_score,
        energy=energy,
        activity_budget=activity_budget,
        travel_time_min=None  # Will use place.get("travel_time_min", 0)
    )
