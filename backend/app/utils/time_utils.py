# backend/app/utils/time_utils.py

from datetime import datetime, timedelta
import pytz


VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def parse_vn_date(text: str) -> str:
    """
    Accepts formats like:
    - 12/03/2025
    - 2025-03-12
    - ngày 12 tháng 3
    """
    text = text.strip()

    # Format dd/mm/yyyy
    if "/" in text:
        d, m, y = text.split("/")
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"

    # Already ISO
    if len(text) == 10 and text[4] == "-":
        return text

    # Natural language fallback
    return datetime.now(VN_TZ).date().isoformat()


def current_vn_time_str():
    return datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
