# backend/app/utils/modify_plan_extractor.py

from app.core.llm import call_gpt_nano

SYSTEM_PROMPT = """
Bạn là AI phân tích yêu cầu chỉnh sửa kế hoạch du lịch.
Hãy xác định ACTION mà người dùng muốn thay đổi trong lịch trình:

Các action:
- change_dates
- change_budget
- replace_hotel
- replace_activity
- add_activity
- remove_activity
- adjust_energy
- adjust_spending_style
- refine_day_plan

Trả về JSON:
{
    "action": "...",
    "details": { ... }
}
"""


async def extract_modify_action(user_prompt: str) -> dict:
    resp = await call_gpt_nano(
        system=SYSTEM_PROMPT,
        user=user_prompt
    )

    try:
        return resp["json"]
    except:
        return {"action": "unknown", "details": {}}
