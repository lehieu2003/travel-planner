# backend/app/core/llm.py

import os
from typing import Dict, Any
from openai import OpenAI

from app.core.config_loader import settings


# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# GPT-nano: LIGHTWEIGHT REASONING (cheap)
# ---------------------------------------------------------------------------
def _gpt_nano(prompt: str) -> str:
    completion = client.chat.completions.create(
        model="gpt-4.1-nano",   # cheapest reasoning-capable model
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return completion.choices[0].message.content


# ---------------------------------------------------------------------------
# GPT-mini: NATURAL LANGUAGE OUTPUT (itinerary summary)
# ---------------------------------------------------------------------------
def _gpt_mini(prompt: str) -> str:
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return completion.choices[0].message.content


# ---------------------------------------------------------------------------
# EXTRACT USER HARD/SOFT CONSTRAINTS
# ---------------------------------------------------------------------------
def extract_constraints(user_message: str) -> Dict[str, Any]:
    prompt = f"""
Bạn là AI chuyên lập kế hoạch du lịch. 
Hãy trích xuất 2 nhóm ràng buộc từ message của người dùng:

1. HARD CONSTRAINTS (bắt buộc):
- destination
- origin (nếu có)
- dates (ngày đi - ngày về)
- number of days (nếu suy ra được)
- budget (VND)
- must-visit places
- adults/children
- time constraints

2. SOFT CONSTRAINTS (ưu tiên):
- travel style (chill / khám phá / thiên nhiên / food tour)
- personal interests (coffee, food, trekking, sống ảo...)
- energy level
- spending style (budget / balanced / premium)

User message:
"{user_message}"

Trả về ONLY JSON như sau:
{{
  "hard": {{}},
  "soft": {{}}
}}
    """

    raw = _gpt_nano(prompt)

    try:
        return eval(raw)  # because GPT returns JSON-like text
    except:
        return {"hard": {}, "soft": {}}


# ---------------------------------------------------------------------------
# DETECT PLAN MODIFICATION INTENT
# ---------------------------------------------------------------------------
def detect_plan_modification(user_message: str, last_plan: Dict[str, Any]):
    prompt = f"""
User message: "{user_message}"

Nếu user muốn thay đổi kế hoạch, phân loại thành:
- "add"
- "remove"
- "replace"
- "change_budget"
- "change_days"
- "none"

Và mô tả thay đổi.

Output JSON:
{{
  "action": "...",
  "modification": {{}}
}}
"""

    raw = _gpt_nano(prompt)
    try:
        return eval(raw)
    except:
        return {"action": "none", "modification": {}}


# ---------------------------------------------------------------------------
# GPT MINI: NATURAL LANGUAGE SUMMARY
# ---------------------------------------------------------------------------
def rewrite_itinerary_summary(itinerary: Dict[str, Any]) -> str:
    prompt = f"""
Dựa vào lịch trình dưới đây, hãy viết phần mô tả ngắn gọn, hấp dẫn bằng tiếng Việt.

Lịch trình:
{itinerary}

Viết 3–5 câu, súc tích và chuyên nghiệp.
    """
    return _gpt_mini(prompt)


# ---------------------------------------------------------------------------
# GPT PREFERENCE SCORE (0 → 1)
# ---------------------------------------------------------------------------
def gpt_preference_score(activity: Dict[str, Any],
                         soft_constraints: Dict[str, Any],
                         long_term_preferences: Dict[str, Any]) -> float:

    prompt = f"""
Đánh giá mức độ người dùng sẽ thích địa điểm này (0 đến 1).

Địa điểm:
{activity}

SOFT CONSTRAINTS:
{soft_constraints}

LONG-TERM PREF:
{long_term_preferences}

Trả về JSON:
{{ "score": 0.xx }}
"""

    raw = _gpt_nano(prompt)

    try:
        return eval(raw)["score"]
    except:
        return 0.5
