# backend/app/models/preference_models.py

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


# ----------------------------------------------------------
# HARD CONSTRAINTS (must always follow)
# ----------------------------------------------------------
class HardConstraints(BaseModel):
    destination: Optional[str] = None
    origin: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    budget_vnd: Optional[int] = None
    must_visit: List[str] = Field(default_factory=list)
    adults: Optional[int] = 1
    children: Optional[int] = 0


# ----------------------------------------------------------
# SOFT CONSTRAINTS (preferences)
# ----------------------------------------------------------
class SoftConstraints(BaseModel):
    energy: str = "medium"                 # low / medium / high
    spending_style: str = "balanced"       # budget / balanced / premium
    travel_style: str = "balanced"         # chill / adventure / foodie / cultural
    pace: str = "moderate"                 # slow / moderate / fast
    interests: List[str] = Field(default_factory=list)
    disliked_categories: List[str] = Field(default_factory=list)
    preferred_categories: List[str] = Field(default_factory=list)


# ----------------------------------------------------------
# LONG-TERM USER PREFERENCES (persisted)
# ----------------------------------------------------------
class LongTermPreferences(BaseModel):
    """
    Stable user traits (learned across many trips).
    Stored in SQLite long_memory.
    """
    food_preferences: List[str] = Field(default_factory=list)
    drink_preferences: List[str] = Field(default_factory=list)
    culture_preferences: List[str] = Field(default_factory=list)
    activity_preferences: List[str] = Field(default_factory=list)
    disliked: List[str] = Field(default_factory=list)

    # Derived signals
    high_energy_bias: float = 0.0
    premium_bias: float = 0.0
    outdoor_bias: float = 0.0
    
    # Trip counter
    trips_planned: int = 0


# ----------------------------------------------------------
# SHORT-TERM PREFERENCES (conversation-level)
# ----------------------------------------------------------
class ShortTermPreferences(BaseModel):
    """
    Applies only INSIDE the current conversation.
    Gets reset when new conversation starts.
    """
    temp_dislikes: List[str] = Field(default_factory=list)
    temp_likes: List[str] = Field(default_factory=list)
    latest_constraints: Dict[str, Any] = Field(default_factory=dict)


# ----------------------------------------------------------
# PREFERENCE SCORE RESULT FOR ACTIVITIES
# ----------------------------------------------------------
class ActivityPreferenceScore(BaseModel):
    """
    Represents how likely a user will enjoy a place.
    Used to combine GPT-nano preference + rule-based matching.
    """
    gpt_score: float = 0.0           # from GPT-nano
    category_alignment: float = 0.0  # based on interests
    cost_alignment: float = 0.0      # based on spending style
    energy_alignment: float = 0.0    # how suitable for user's energy
    final_score: float = 0.0


# ----------------------------------------------------------
# MASTER AGGREGATED MODEL
# ----------------------------------------------------------
class UserPreferenceBundle(BaseModel):
    """
    The orchestrator combines these 4 layers for planning decisions.
    """
    hard: HardConstraints
    soft: SoftConstraints
    long_term: Optional[LongTermPreferences] = None
    short_term: Optional[ShortTermPreferences] = None

    def to_dict(self):
        return {
            "hard_constraints": self.hard.dict(),
            "soft_constraints": self.soft.dict(),
            "long_memory": self.long_term.dict() if self.long_term else {},
            "short_memory": self.short_term.dict() if self.short_term else {},
        }


# ----------------------------------------------------------
# RULE-BASED CATEGORY MATCHING
# ----------------------------------------------------------
CATEGORY_KEYWORDS = {
    "food": ["restaurant", "street food", "food", "ăn", "quán ăn", "đặc sản"],
    "drink": ["cafe", "coffee", "bar", "pub", "trà", "tea", "đồ uống", "sinh tố", "nước ép", "trà sữa", "giải khát", "nước mía", "smoothie", "juice", "bubble tea"],
    "museum": ["museum", "bảo tàng"],
    "park": ["park", "công viên"],
    "shopping": ["shopping", "mall", "trung tâm thương mại"],
    "attraction": ["attraction", "địa điểm", "check-in", "đi chơi", "khu du lịch", "công viên giải trí", "amusement park", "theme park", "bãi biển", "beach"],
    "nightlife": ["bar", "pub", "night", "club", "karaoke", "đêm"],
}


def match_category(place_name: str, interests: List[str]) -> float:
    name_lower = place_name.lower()
    for interest in interests:
        if interest.lower() in name_lower:
            return 1.0
    return 0.0


# ----------------------------------------------------------
# COST ALIGNMENT SCORING
# ----------------------------------------------------------
def cost_alignment(place_cost: int, spending_style: str) -> float:
    if spending_style == "budget":
        return max(0, 1 - (place_cost / 300_000))  # prefer <300k
    elif spending_style == "premium":
        return 0.8 if place_cost > 500_000 else 0.4
    else:
        return 1 - abs(place_cost - 300_000) / 600_000  # balanced users prefer mid-range


# ----------------------------------------------------------
# ENERGY ALIGNMENT SCORING
# ----------------------------------------------------------
def energy_alignment(duration_min: int, energy_level: str) -> float:
    if energy_level == "low":
        return max(0, 1 - duration_min / 180)  # prefer <3h
    if energy_level == "high":
        return min(1, duration_min / 120)      # prefer >2h
    return 1 - abs(duration_min - 120) / 300   # medium prefers ~2h


# ----------------------------------------------------------
# FINAL AGGREGATED SCORE COMBINER
# ----------------------------------------------------------
def compute_preference_score(
    activity: Dict[str, Any],
    gpt_score: float,
    soft: SoftConstraints
) -> ActivityPreferenceScore:

    place_name = activity.get("name", "")
    cost = activity.get("estimated_cost_vnd", 0)
    duration = activity.get("duration_min", 90)

    category_match = match_category(place_name, soft.interests)
    cost_score = cost_alignment(cost, soft.spending_style)
    energy_score = energy_alignment(duration, soft.energy)

    final = (
        0.4 * gpt_score +
        0.25 * category_match +
        0.20 * cost_score +
        0.15 * energy_score
    )

    return ActivityPreferenceScore(
        gpt_score=gpt_score,
        category_alignment=category_match,
        cost_alignment=cost_score,
        energy_alignment=energy_score,
        final_score=round(final, 4)
    )
