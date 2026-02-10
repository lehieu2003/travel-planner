# backend/app/utils/constraint_extractor.py

from app.core.llm import call_gpt_nano


SYSTEM_PROMPT = """
Bạn là AI chuyên phân tích yêu cầu du lịch.
Nhiệm vụ: Trích xuất HARD CONSTRAINTS và SOFT CONSTRAINTS từ đoạn hội thoại tiếng Việt.

HARD = bắt buộc:
- destination
- origin (nếu có)
- date_start
- date_end
- budget_vnd
- must_visit (list)

SOFT = sở thích:
- spending_style: budget / balanced / premium
- energy: low / medium / high
- interests: [food, cafe, museum, night, trekking,...]
- disliked_categories
"""


async def extract_constraints_from_text(user_prompt: str) -> dict:
    response = await call_gpt_nano(
        system=SYSTEM_PROMPT,
        user=f"Phân tích yêu cầu: {user_prompt}. Trả về JSON."
    )

    try:
        data = response["json"]
    except:
        data = {}

    hard = data.get("hard", {}) or {}
    soft = data.get("soft", {}) or {}

    return {
        "hard_constraints": hard,
        "soft_constraints": soft,
    }
