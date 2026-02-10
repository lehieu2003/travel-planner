# backend/app/agents/llm_agent.py

import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional, Dict, Any, Tuple, List
import json
import re
from app.core.logger import logger

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing in environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)


class LLMAgent:
    """
    GPT-enabled agent used for:
    - Natural-language message parsing (VN)
    - User preference extraction
    - Budget/date/city extraction
    - Re-ranking activities
    - Generating itinerary descriptions
    - Chatting with users (generate_chat_response)
    - Confirmation messages (generate_confirmation_message)
    
    Model đang sử dụng: gpt-4o-mini
    - Ưu điểm: Rẻ, nhanh
    - Nhược điểm: Có thể không hiểu tốt các prompt phức tạp
    - Đề xuất nâng cấp: gpt-4o hoặc gpt-4o-mini với prompt tốt hơn
    """

    # -----------------------------
    # 1. Extract structured plan info from a VN message
    # -----------------------------
    async def extract_plan_data(self, message: str, conversation_history: Optional[list] = None, user_configs: Optional[dict] = None) -> dict:
        """
        Uses gpt-4o-mini for semantic extraction
        (cheap model → perfect for analysis)
        
        Args:
            message: User's message
            conversation_history: Previous conversation messages
            user_configs: User configuration from database (energy_level, budget_min, budget_max, preference_json)
        """

        # Build context from conversation history if available
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            history_context = "\n\nLịch sử cuộc trò chuyện trước đó:\n"
            # Use all messages in the conversation (up to 100 for very long sessions)
            messages_to_include = conversation_history[-100:] if len(conversation_history) > 100 else conversation_history
            for msg in messages_to_include:
                role = "Người dùng" if msg.get("role") == "user" else "TravelGPT"
                content = msg.get("content", "")
                history_context += f"- {role}: {content}\n"
            history_context += "\n⚠️ QUAN TRỌNG: Nếu trong lịch sử cuộc trò chuyện trên đã có thông tin về địa điểm (city), ngân sách (budget), hoặc số ngày (duration), bạn PHẢI sử dụng thông tin đó ngay cả khi người dùng không đề cập lại trong câu nói hiện tại. Ví dụ:\n"
            history_context += "- Nếu trong lịch sử đã có \"Đà Lạt\" và người dùng chỉ nói \"3 triệu 4 ngày\", bạn PHẢI extract city=\"Đà Lạt\" từ lịch sử.\n"
            history_context += "- Nếu trong lịch sử đã có \"3 triệu\" và người dùng chỉ nói \"Đà Lạt 4 ngày\", bạn PHẢI extract budget_vnd=3000000 từ lịch sử.\n"
            history_context += "- Nếu trong lịch sử đã có \"4 ngày\" và người dùng chỉ nói \"Đà Lạt 3 triệu\", bạn PHẢI extract duration_days=4 từ lịch sử.\n"
            history_context += "- Tóm lại: Tổng hợp thông tin từ CẢ lịch sử VÀ câu nói hiện tại để có đầy đủ thông tin nhất.\n"

        # Build user configs context
        user_configs_context = ""
        if user_configs:
            user_configs_context = "\n\n📋 THÔNG TIN NGƯỜI DÙNG TỪ HỒ SƠ:\n"
            if user_configs.get("energy_level"):
                user_configs_context += f"- Mức năng lượng: {user_configs['energy_level']} (low/medium/high)\n"
            if user_configs.get("budget_min") or user_configs.get("budget_max"):
                budget_info = ""
                if user_configs.get("budget_min") and user_configs.get("budget_max"):
                    budget_info = f"{user_configs['budget_min']:,} - {user_configs['budget_max']:,} VNĐ".replace(",", ".")
                elif user_configs.get("budget_min"):
                    budget_info = f"Tối thiểu: {user_configs['budget_min']:,} VNĐ".replace(",", ".")
                elif user_configs.get("budget_max"):
                    budget_info = f"Tối đa: {user_configs['budget_max']:,} VNĐ".replace(",", ".")
                if budget_info:
                    user_configs_context += f"- Ngân sách: {budget_info}\n"
            
            # Parse preferences_json if available
            preferences_list = []
            if user_configs.get("preferences_json"):
                try:
                    if isinstance(user_configs["preferences_json"], str):
                        preferences_list = json.loads(user_configs["preferences_json"])
                    elif isinstance(user_configs["preferences_json"], list):
                        preferences_list = user_configs["preferences_json"]
                except:
                    preferences_list = []
            
            if preferences_list:
                user_configs_context += f"- Sở thích đã lưu: {', '.join(preferences_list)}\n"
            
            user_configs_context += "\n⚠️ QUAN TRỌNG: Sử dụng thông tin từ hồ sơ người dùng để:\n"
            user_configs_context += "- Nếu người dùng không đề cập mức năng lượng (energy), sử dụng energy_level từ hồ sơ\n"
            user_configs_context += "- Nếu người dùng không đề cập ngân sách cụ thể, ưu tiên sử dụng budget_min/budget_max từ hồ sơ (có thể lấy trung bình hoặc max)\n"
            user_configs_context += "- Nếu người dùng không đề cập sở thích cụ thể, thêm các sở thích từ preferences_json vào interests\n"
            user_configs_context += "- Tuy nhiên, nếu người dùng đề cập rõ ràng thông tin mới, ưu tiên thông tin từ câu nói của người dùng\n"

        prompt = f"""
Bạn là AI Travel Planner tiếng Việt. Hãy phân tích câu nói của người dùng
và trích xuất thành JSON.{history_context}{user_configs_context}

Người dùng nói:
---
{message}
---

Trả về JSON với format:

{{
  "budget_vnd": <số VND dạng số nguyên hoặc null>,
  "energy": "low|medium|high",
  "city": "<tên thành phố hoặc null>",
  "location_type": "<beach|mountain|city|nature|historical|null>",
  "duration_days": <số ngày dạng số nguyên hoặc null, ví dụ: "5 ngày 4 đêm" -> 5, "cuối tuần" -> 2, "t7 với cn" -> 2>,
  "date_range": {{
      "start": "YYYY-MM-DD" hoặc null,
      "end": "YYYY-MM-DD" hoặc null
  }},
  "preferences": {{
      "food": "<sở thích món ăn hoặc null>",
      "activities": "<loại hoạt động yêu thích hoặc null>",
      "accommodation": "<loại khách sạn hoặc null>",
      "style": "<chill|nature|luxury|coffee|explore|romantic hoặc null>"
  }},
  "is_modification": <true nếu người dùng muốn chỉnh sửa lịch trình hiện tại, false nếu là yêu cầu mới>,
  "modification_type": "<duration|budget|activities|dates|preferences|other hoặc null>",
  "request_type": "<itinerary|list|restaurant_list|hotel_list|activity_list hoặc null>",
  "list_category": "<restaurant|hotel|activity hoặc null>"
}}

QUAN TRỌNG về budget_vnd:
- budget_vnd PHẢI là SỐ NGUYÊN (integer), KHÔNG phải string, KHÔNG phải null nếu có thông tin về ngân sách.
- Nếu người dùng nói "7 triệu" hoặc "7tr", BẮT BUỘC phải convert thành 7000000 (7 * 1,000,000).
- Nếu người dùng nói "5 triệu" hoặc "5tr", convert thành 5000000.
- Nếu người dùng nói "10 triệu" hoặc "10tr", convert thành 10000000.
- Nếu người dùng nói "3 triệu", convert thành 3000000.
- Nếu người dùng đã nói số cụ thể như "7000000", giữ nguyên số đó.
- Công thức: số_triệu * 1,000,000 = budget_vnd
- Nếu người dùng KHÔNG đề cập ngân sách trong câu nói hiện tại, nhưng đã đề cập trong lịch sử cuộc trò chuyện trước đó, BẮT BUỘC phải extract budget_vnd từ lịch sử.
- Ví dụ: Nếu lịch sử có "3 triệu" và người dùng chỉ nói "Đà Lạt 4 ngày", bạn PHẢI extract budget_vnd=3000000 từ lịch sử.
- CHỈ để budget_vnd là null khi KHÔNG có bất kỳ thông tin nào về ngân sách trong CẢ câu nói hiện tại VÀ lịch sử cuộc trò chuyện.
- Ví dụ: "Sapa mùa đông ngân sách 7 triệu" -> budget_vnd: 7000000 (KHÔNG phải null, KHÔNG phải string "7 triệu")

QUAN TRỌNG về city và location_type:
- Tên thành phố có thể là tiếng Việt (Hà Nội, Đà Lạt, Phú Quốc...) hoặc tiếng Anh/quốc tế (Cebu, Bangkok, Tokyo, Paris...).
- Tên thành phố có thể được viết KHÔNG DẤU (ví dụ: "da lat", "ha noi", "phu quoc", "sapa") - BẮT BUỘC phải nhận diện và convert thành tên có dấu chuẩn (ví dụ: "da lat" -> "Đà Lạt", "ha noi" -> "Hà Nội").
- Các ví dụ về tên thành phố tiếng Việt phổ biến:
  + "da lat" / "đà lạt" / "dalat" -> "Đà Lạt" (QUAN TRỌNG: Phải nhận diện được cả "da lat" và "đà lạt")
  + "ha noi" / "hà nội" / "hanoi" -> "Hà Nội"
  + "ho chi minh" / "hồ chí minh" / "hcm" / "sai gon" / "sài gòn" -> "Hồ Chí Minh"
  + "phu quoc" / "phú quốc" -> "Phú Quốc"
  + "sapa" / "sa pa" -> "Sapa"
  + "hue" / "huế" -> "Huế"
  + "da nang" / "đà nẵng" -> "Đà Nẵng"
  + "nha trang" -> "Nha Trang"
- Nếu người dùng đề cập tên địa điểm trong câu nói hiện tại, hãy extract chính xác tên đó và convert về dạng chuẩn có dấu (ví dụ: "cebu" -> "Cebu", "bangkok" -> "Bangkok", "da lat" -> "Đà Lạt").
- Nếu người dùng KHÔNG đề cập địa điểm trong câu nói hiện tại, nhưng đã đề cập trong lịch sử cuộc trò chuyện trước đó, BẮT BUỘC phải extract city từ lịch sử.
- Ví dụ: Nếu lịch sử có "Đà Lạt" và người dùng chỉ nói "3 triệu 4 ngày", bạn PHẢI extract city="Đà Lạt" từ lịch sử.
- ⚠️ VÍ DỤ QUAN TRỌNG: "đà lạt 3 ngày 2 đêm" -> city: "Đà Lạt", duration_days: 3 (KHÔNG phải null)
- ⚠️ VÍ DỤ QUAN TRỌNG: "da lat 3 ngay 2 dem" -> city: "Đà Lạt", duration_days: 3 (KHÔNG phải null)
- ⚠️ VÍ DỤ QUAN TRỌNG: "đà lạt" -> city: "Đà Lạt" (KHÔNG phải null)
- KHÔNG BAO GIỜ extract các từ như "sửa", "thay đổi", "đổi", "chỉnh" thành city name - đây là động từ chỉnh sửa, không phải tên địa điểm.

QUAN TRỌNG về location_type (LOẠI ĐỊA ĐIỂM):
- Nếu người dùng chỉ đề cập LOẠI địa điểm mà KHÔNG có tên thành phố cụ thể, BẮT BUỘC phải extract location_type.
- Các từ khóa cho location_type:
  + "biển", "bãi biển", "đi biển", "thành phố biển", "beach", "coast" -> location_type: "beach"
  + "núi", "đi núi", "vùng núi", "mountain", "hill" -> location_type: "mountain"
  + "thành phố", "city", "đô thị" -> location_type: "city"
  + "thiên nhiên", "nature", "rừng", "forest" -> location_type: "nature"
  + "lịch sử", "historical", "di tích", "cổ kính" -> location_type: "historical"
- Ví dụ QUAN TRỌNG:
  + "tôi muốn đi biển" -> city: null, location_type: "beach"
  + "muốn đi núi" -> city: null, location_type: "mountain"
  + "thành phố biển" -> city: null, location_type: "beach"
  + "đi biển 3 ngày" -> city: null, location_type: "beach", duration_days: 3
- Nếu người dùng đề cập CẢ tên thành phố VÀ loại địa điểm, ưu tiên extract city (ví dụ: "đi biển Nha Trang" -> city: "Nha Trang", location_type: "beach").
- CHỈ để location_type là null khi người dùng đề cập tên thành phố cụ thể hoặc không có thông tin về loại địa điểm.

- CHỈ để city là null khi KHÔNG có thông tin về địa điểm trong CẢ câu nói hiện tại VÀ lịch sử cuộc trò chuyện.

QUAN TRỌNG về duration_days:
⚠️ QUAN TRỌNG NHẤT: Nếu người dùng đề cập các ngày trong tuần hoặc cụm từ về thời gian, BẮT BUỘC phải tự tính số ngày và extract vào duration_days. KHÔNG BAO GIỜ để duration_days là null khi có thông tin về thời gian.

Các cụm từ về thời gian BẮT BUỘC phải extract duration_days:
1. "cuối tuần" / "cuối tuần này" / "weekend" / "weekend này" -> duration_days: 2 (thứ 7 và chủ nhật = 2 ngày)
   Ví dụ: "Đi Hà Nội cuối tuần này" -> duration_days: 2
   Ví dụ: "cuối tuần 1 triệu" -> duration_days: 2
   Ví dụ: "weekend này đi Đà Lạt" -> duration_days: 2
   
2. "t7 với cn" / "thứ 7 và chủ nhật" / "t7 cn" / "thứ 7 chủ nhật" -> duration_days: 2
   Ví dụ: "t7 với cn" -> duration_days: 2
   Ví dụ: "thứ 7 và chủ nhật" -> duration_days: 2
   
3. "thứ 2 đến thứ 5" / "t2 đến t5" / "từ thứ 2 đến thứ 5" -> duration_days: 4
   
4. "thứ 6 đến chủ nhật" / "t6 đến cn" / "từ thứ 6 đến chủ nhật" -> duration_days: 3
   
5. "thứ 2, thứ 3, thứ 4" / "t2, t3, t4" -> duration_days: 3 (đếm số ngày được liệt kê)
   
6. "đầu tuần" -> duration_days: 2 hoặc 3 (tùy ngữ cảnh, thường là thứ 2-thứ 3 hoặc thứ 2-thứ 4)

7. Nếu người dùng liệt kê nhiều ngày riêng lẻ (ví dụ: "t2, t3, t4, t5"), đếm số ngày được liệt kê -> duration_days: 4

8. Nếu người dùng nói khoảng thời gian (ví dụ: "từ thứ 2 đến thứ 5"), tính số ngày trong khoảng đó (bao gồm cả ngày đầu và ngày cuối) -> duration_days: 4

Các pattern số ngày trực tiếp:
- "3 ngày" / "5 ngày 4 đêm" / "tôi muốn 5 ngày" -> extract số ngày đầu tiên vào duration_days
  ⚠️ VÍ DỤ QUAN TRỌNG: "5 ngày 4 đêm" -> duration_days: 5 (KHÔNG phải null, KHÔNG phải 4)
  ⚠️ VÍ DỤ QUAN TRỌNG: "3 ngày 2 đêm" -> duration_days: 3 (lấy số ngày đầu tiên, không phải số đêm, KHÔNG phải null)
  ⚠️ VÍ DỤ QUAN TRỌNG: "đà lạt 3 ngày 2 đêm" -> duration_days: 3 (KHÔNG phải null)
  ⚠️ VÍ DỤ QUAN TRỌNG: "da lat 3 ngay 2 dem" -> duration_days: 3 (KHÔNG phải null)
  ⚠️ VÍ DỤ QUAN TRỌNG: "3 ngày 2 đêm" -> duration_days: 3 (KHÔNG phải null, KHÔNG phải 2)
- "sửa thành lịch 4 ngày" -> duration_days: 4
- "sửa thành 4 ngày" -> duration_days: 4
- "thay đổi thành 5 ngày" -> duration_days: 5
- "đổi thành lịch 3 ngày" -> duration_days: 3
- QUAN TRỌNG: Khi thấy pattern "X ngày Y đêm", BẮT BUỘC phải extract X (số ngày) vào duration_days, KHÔNG phải Y (số đêm). KHÔNG BAO GIỜ để duration_days là null khi có pattern này.

Extract từ lịch sử cuộc trò chuyện:
- Nếu người dùng KHÔNG đề cập số ngày trong câu nói hiện tại, nhưng đã đề cập trong lịch sử cuộc trò chuyện trước đó, BẮT BUỘC phải extract duration_days từ lịch sử.
- Ví dụ: Nếu lịch sử có "4 ngày 3 đêm" và người dùng chỉ nói "Đà Lạt 3 triệu", bạn PHẢI extract duration_days=4 từ lịch sử.
- Ví dụ: Nếu lịch sử có "t7 với cn" và người dùng chỉ nói "Hà Nội 1 triệu", bạn PHẢI extract duration_days=2 từ lịch sử.
- Ví dụ: Nếu lịch sử có "cuối tuần này" và người dùng chỉ nói "1 triệu", bạn PHẢI extract duration_days=2 từ lịch sử.

QUAN TRỌNG về phân biệt "ngày cụ thể" vs "tổng số ngày":
⚠️ CỰC KỲ QUAN TRỌNG: Phân biệt giữa việc chỉ định NGÀY CỤ THỂ trong itinerary và việc chỉ định TỔNG SỐ NGÀY của chuyến đi.

- Pattern "ngày X, Y" hoặc "ngày X và Y" hoặc "vào ngày X, Y" = CHỈ ĐỊNH NGÀY CỤ THỂ trong itinerary hiện có
  + Ví dụ: "thêm đồ ăn vào ngày 3,4" -> KHÔNG extract duration_days, đây là chỉ định ngày cụ thể để thêm activities
  + Ví dụ: "thêm quán cà phê vào ngày 2,3" -> KHÔNG extract duration_days, đây là chỉ định ngày cụ thể
  + Ví dụ: "sửa ngày 1 và ngày 2" -> KHÔNG extract duration_days, đây là chỉ định ngày cụ thể
  + Khi thấy pattern này trong modification request, duration_days PHẢI là null hoặc giữ nguyên từ lịch sử
  
- Pattern "X ngày" hoặc "X ngày Y đêm" = TỔNG SỐ NGÀY của chuyến đi
  + Ví dụ: "3 ngày" -> duration_days: 3
  + Ví dụ: "5 ngày 4 đêm" -> duration_days: 5
  + Ví dụ: "sửa thành 4 ngày" -> duration_days: 4
  
- Cách phân biệt:
  + Nếu có từ "vào ngày", "ngày X, Y", "ngày X và Y" + có từ khóa modification (thêm, sửa, đổi) -> CHỈ ĐỊNH NGÀY CỤ THỂ, KHÔNG extract duration_days
  + Nếu có pattern "X ngày" hoặc "X ngày Y đêm" mà KHÔNG có "vào ngày" hoặc "ngày X, Y" -> TỔNG SỐ NGÀY, extract duration_days = X
  
- Ví dụ cụ thể:
  + "thêm đồ ăn vào ngày 3,4" -> duration_days: null (hoặc giữ nguyên từ lịch sử), đây là chỉ định ngày cụ thể
  + "thêm quán cà phê vào ngày 2 và 3" -> duration_days: null (hoặc giữ nguyên từ lịch sử), đây là chỉ định ngày cụ thể
  + "muốn thêm đồ ăn vào ngày 1,2,3" -> duration_days: null (hoặc giữ nguyên từ lịch sử), đây là chỉ định ngày cụ thể
  + "sửa thành 4 ngày" -> duration_days: 4, đây là thay đổi tổng số ngày
  + "tôi muốn 3 ngày" -> duration_days: 3, đây là tổng số ngày

Quy tắc chung:
- duration_days PHẢI là SỐ NGUYÊN (integer), KHÔNG phải string.
- CHỈ để duration_days là null khi KHÔNG có bất kỳ thông tin nào về số ngày hoặc thời gian trong CẢ câu nói hiện tại VÀ lịch sử cuộc trò chuyện.
- Ưu tiên cao nhất: Extract duration_days từ các cụm từ về thời gian (cuối tuần, t7 với cn, etc.) trước khi để null.
- QUAN TRỌNG: Khi thấy pattern "vào ngày X, Y" hoặc "ngày X, Y" trong modification request, KHÔNG extract duration_days từ các số này.

QUAN TRỌNG về dates:
- Nếu người dùng chỉ nói số ngày (ví dụ: "3 ngày", "6 ngày 5 đêm") mà không có ngày cụ thể, 
  hãy để start và end là null (hệ thống sẽ tự động tạo dates mặc định dựa trên duration_days).
- Nếu người dùng có đề cập ngày cụ thể, hãy parse thành format YYYY-MM-DD.
- Nếu không có thông tin về thời gian, để cả start và end là null.

QUAN TRỌNG về modification:
- Nếu có lịch sử cuộc trò chuyện trước đó VÀ người dùng muốn chỉnh sửa/thay đổi lịch trình đã có, 
  hãy đặt is_modification = true và chỉ định modification_type phù hợp.
- Các từ khóa modification: "sửa", "thay đổi", "đổi", "chỉnh sửa", "muốn", "cần"
- Các ví dụ về modification request:
  + "sửa thành lịch 4 ngày" -> is_modification: true, modification_type: "duration", duration_days: 4, city: null
  + "sửa thành 5 ngày" -> is_modification: true, modification_type: "duration", duration_days: 5, city: null
  + "thay đổi thành 4 ngày" -> is_modification: true, modification_type: "duration", duration_days: 4, city: null
  + "đổi thành lịch 3 ngày" -> is_modification: true, modification_type: "duration", duration_days: 3, city: null
  + "tôi muốn 4 ngày 3 đêm" -> is_modification: true, modification_type: "duration", duration_days: 4
  + "thay đổi ngân sách thành 8 triệu" -> is_modification: true, modification_type: "budget", budget_vnd: 8000000
  + "tôi muốn lịch 4 ngày 3 đêm" -> is_modification: true, modification_type: "duration", duration_days: 4
  + "muốn thêm ngày" -> is_modification: true, modification_type: "duration"
- QUAN TRỌNG: Khi thấy các từ "sửa thành", "thay đổi thành", "đổi thành" + số ngày, 
  BẮT BUỘC phải đặt is_modification = true, modification_type = "duration", và extract số ngày vào duration_days.
- Khi là modification request về duration, KHÔNG extract "sửa", "thay đổi", "đổi" thành city name.
- Nếu người dùng chỉ nói số ngày mới mà không đề cập địa điểm/ngân sách mới trong câu nói hiện tại, 
  nhưng có lịch sử cuộc trò chuyện trước đó, đây là modification request.
- Nếu là yêu cầu mới hoàn toàn (không có lịch sử hoặc người dùng đề cập địa điểm/ngân sách mới rõ ràng), 
  đặt is_modification = false.

QUAN TRỌNG về request_type và list_category:
- Nếu người dùng chỉ muốn DANH SÁCH đơn giản (không phải lịch trình đầy đủ), đặt request_type = "list" và list_category phù hợp.
- Các từ khóa cho danh sách: "danh sách", "liệt kê", "list", "gợi ý", "cho tôi xem", "muốn xem", "chỉ cần danh sách", "không cần lịch trình", "chỉ cần", "cho tôi", "quán ăn nổi tiếng", "nhà hàng nổi tiếng"
- Các ví dụ về request list:
  + "tôi muốn danh sách quán ăn" -> request_type: "list", list_category: "restaurant"
  + "cho tôi danh sách nhà hàng" -> request_type: "list", list_category: "restaurant"
  + "liệt kê các quán ăn" -> request_type: "list", list_category: "restaurant"
  + "chỉ cần quán ăn" -> request_type: "list", list_category: "restaurant"
  + "cho tôi quán ăn nổi tiếng" -> request_type: "list", list_category: "restaurant"
  + "cho tôi quán ăn" -> request_type: "list", list_category: "restaurant"
  + "quán ăn nổi tiếng" -> request_type: "list", list_category: "restaurant"
  + "cho tôi thêm quán cà phê" -> request_type: "list", list_category: "drink"
  + "thêm quán cà phê" -> request_type: "list", list_category: "drink"
  + "cho tôi danh sách quán cà phê" -> request_type: "list", list_category: "drink"
  + "quán cà phê nổi tiếng" -> request_type: "list", list_category: "drink"
  + "cà phê" -> request_type: "list", list_category: "drink"
  + "tôi muốn danh sách khách sạn" -> request_type: "list", list_category: "hotel"
  + "cho tôi xem các khách sạn" -> request_type: "list", list_category: "hotel"
  + "danh sách địa điểm tham quan" -> request_type: "list", list_category: "activity"
  + "tôi muốn danh sách quán ăn ko phải lịch trình" -> request_type: "list", list_category: "restaurant"
  + "chỉ cần danh sách nhà hàng" -> request_type: "list", list_category: "restaurant"
- QUAN TRỌNG: Khi người dùng chỉ đề cập đến loại địa điểm (ví dụ: "chỉ cần quán ăn", "cho tôi quán ăn nổi tiếng", "quán ăn") mà KHÔNG đề cập đến "lịch trình", "kế hoạch", "plan", hoặc các từ khóa tạo lịch trình khác, 
  BẮT BUỘC phải đặt request_type = "list" và list_category phù hợp.
- Nếu người dùng muốn lịch trình đầy đủ (có đề cập "lịch trình", "kế hoạch", "plan", hoặc có đầy đủ thông tin như city + budget + duration), 
  đặt request_type = "itinerary" hoặc null (mặc định là itinerary).
- list_category có thể là: "restaurant" (quán ăn, nhà hàng), "drink" (quán cà phê, cà phê, cafe, bar, pub, đồ uống), "hotel" (khách sạn, nơi ở), "activity" (địa điểm tham quan, hoạt động).
- Nếu request_type = "list" nhưng không rõ category, hãy suy luận từ ngữ cảnh:
  + Nếu có từ "quán ăn", "nhà hàng", "ăn uống", "món ăn" -> list_category: "restaurant"
  + Nếu có từ "quán cà phê", "cà phê", "cafe", "coffee", "bar", "pub", "đồ uống", "trà", "tea", "sinh tố", "nước ép", "trà sữa", "giải khát", "nước mía", "smoothie", "juice", "bubble tea" -> list_category: "drink" (QUAN TRỌNG: Phân biệt với restaurant)
  + Nếu có từ "khách sạn", "nơi ở", "chỗ ở", "accommodation" -> list_category: "hotel"
  + Nếu có từ "địa điểm", "thăm quan", "hoạt động", "activities" -> list_category: "activity"
- QUAN TRỌNG: "cà phê", "quán cà phê", "bar", "pub", "đồ uống", "sinh tố", "nước ép", "trà sữa", "giải khát", "nước mía" PHẢI được detect là list_category: "drink", KHÔNG phải "restaurant"

Chỉ trả JSON, không giải thích.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.1,
        )

        try:
            content = response.choices[0].message.content
            if not content:
                logger.warning(f"LLM returned empty content for message: {message[:50]}")
                return {}
            
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                # Remove ```json or ``` at start and end
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)
            
            # Try to extract JSON from content (in case there's extra text)
            # Look for JSON object pattern
            json_start = content.find("{")
            json_end = content.rfind("}")
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_content = content[json_start:json_end + 1]
            else:
                json_content = content
            
            parsed_data = json.loads(json_content)
            logger.info(f"Successfully extracted data: city={parsed_data.get('city')}, duration_days={parsed_data.get('duration_days')}, budget_vnd={parsed_data.get('budget_vnd')}")
            return parsed_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for message '{message[:50]}': {e}")
            logger.error(f"LLM response content: {content[:500] if 'content' in locals() else 'N/A'}")
            # Try to extract JSON with regex as fallback
            try:
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
                if json_match:
                    json_str = json_match.group(0)
                    parsed_data = json.loads(json_str)
                    logger.info(f"Successfully extracted data using regex fallback: city={parsed_data.get('city')}, duration_days={parsed_data.get('duration_days')}")
                    return parsed_data
            except:
                pass
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in extract_plan_data for message '{message[:50]}': {e}")
            return {}

    # -----------------------------
    # 2. Extract preferences from conversation history
    # -----------------------------
    async def extract_preferences_from_history(self, conversation_history: list) -> dict:
        """
        Extract user preferences (interests, spending_style, energy, etc.) from conversation history.
        This helps maintain context when modifying plans.
        """
        if not conversation_history or len(conversation_history) == 0:
            return {}
        
        # Build context from user messages only
        user_messages = []
        for msg in conversation_history:
            if msg.get("role") == "user":
                user_messages.append(msg.get("content", ""))
        
        if not user_messages:
            return {}
        
        # Combine all user messages
        history_text = "\n".join([f"- {msg}" for msg in user_messages])
        
        prompt = f"""
Bạn là AI phân tích sở thích người dùng từ lịch sử cuộc trò chuyện.

Lịch sử các message của người dùng:
{history_text}

Hãy trích xuất các sở thích và preferences từ các message trên:
- interests: danh sách các sở thích (ví dụ: ["đồ ăn chay", "bảo tàng", "cà phê", "thiên nhiên"])
- spending_style: budget / balanced / premium
- energy: low / medium / high
- travel_style: chill / adventure / foodie / cultural

Trả về JSON:
{{
    "interests": ["..."],
    "spending_style": "...",
    "energy": "...",
    "travel_style": "..."
}}

Chỉ trả JSON, không giải thích.
"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1,
            )
            
            content = response.choices[0].message.content
            if not content:
                return {}
            
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)
            
            # Extract JSON
            json_start = content.find("{")
            json_end = content.rfind("}")
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_content = content[json_start:json_end + 1]
            else:
                json_content = content
            
            parsed_data = json.loads(json_content)
            logger.info(f"Extracted preferences from history: {parsed_data}")
            return parsed_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in extract_preferences_from_history: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error in extract_preferences_from_history: {e}")
            return {}

    # -----------------------------
    # 3. Re-rank activities (gpt-nano)
    # -----------------------------
    async def rerank_activities(self, activities, user_preferences):
        """
        Sends list of activities + preferences to GPT-4o-mini for scoring.
        """
        prompt = f"""
Bạn là AI giúp đánh giá địa điểm du lịch.

User preferences:
{json.dumps(user_preferences, ensure_ascii=False, indent=2)}

Travel activities:
{json.dumps(activities, ensure_ascii=False, indent=2)}

Trả về danh sách JSON:
[
  {{
    "name": "...",
    "score": <0-1>,
    "reason": "tại sao phù hợp"
  }},
  ...
]

Không thêm chữ khác bên ngoài JSON.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.2,
        )

        try:
            content = response.choices[0].message.content
            if not content:
                return []
            return json.loads(content)
        except:
            return []

    # -----------------------------
    # 4. Generate human-friendly itinerary narrative (gpt-mini)
    # -----------------------------
    async def generate_itinerary_description(self, itinerary: dict, user_prefs: dict):
        """
        Uses gpt-4o-mini to generate itinerary description in the exact required format.
        Format:
        City: <city name>
        Duration: <number of days>
        Budget Range: <min budget> – <max budget>
        
        Places to Visit
        🏛 Places (Sightseeing / Activities)
        ...
        🍽 Food (Restaurants / Local Food)
        ...
        ☕ Coffee Shops
        ...
        Itinerary Comment
        ...
        """
        
        # Extract city, duration, budget from user_prefs
        city = user_prefs.get("city", "")
        # Try to get city from itinerary if not in user_prefs
        if not city:
            city = itinerary.get("destination", "")
        if not city:
            city = "N/A"
        
        duration_days = user_prefs.get("duration", 0)
        if not duration_days:
            # Try to get from itinerary days count
            days = itinerary.get("days", [])
            duration_days = len(days) if days else 0
        
        # Get budget_min and budget_max from user_prefs (user profile) - PRIORITY
        budget_min = user_prefs.get("budget_min")
        budget_max = user_prefs.get("budget_max")
        
        # If not available from user profile, try to get from budget_vnd or itinerary
        if not budget_min or not budget_max:
            budget_vnd = user_prefs.get("budget", 0)
            if not budget_vnd:
                # Try to get from itinerary budget_allocation
                budget_alloc = itinerary.get("budget_allocation", {})
                if budget_alloc:
                    total_budget = (
                        budget_alloc.get("hotel", 0) +
                        budget_alloc.get("activities", 0) +
                        budget_alloc.get("food", 0) +
                        budget_alloc.get("transport", 0)
                    )
                    if total_budget > 0:
                        budget_vnd = total_budget
            
            # Use budget_vnd as fallback if user profile doesn't have min/max
            if not budget_min:
                budget_min = budget_vnd
            if not budget_max:
                budget_max = budget_vnd
        
        # Format budget range
        if budget_min and budget_max:
            budget_min_str = f"{int(budget_min):,}".replace(",", ".")
            budget_max_str = f"{int(budget_max):,}".replace(",", ".")
            budget_range = f"{budget_min_str} – {budget_max_str}"
        elif budget_min:
            budget_str = f"{int(budget_min):,}".replace(",", ".")
            budget_range = f"{budget_str} – {budget_str}"
        elif budget_max:
            budget_str = f"{int(budget_max):,}".replace(",", ".")
            budget_range = f"{budget_str} – {budget_str}"
        else:
            budget_range = "0 – 0"
        
        # Extract all places from itinerary days
        places = []  # Sightseeing/Activities (not food, not coffee)
        food_places = []  # Restaurants/Food
        coffee_places = []  # Coffee shops
        
        days = itinerary.get("days", [])
        seen_places = set()  # To avoid duplicates
        
        # Track statistics for debugging
        total_segments = 0
        skipped_no_activity = 0
        skipped_no_name = 0
        skipped_duplicate = 0
        added_places = 0
        
        for day_idx, day in enumerate(days, 1):
            segments = day.get("segments", [])
            total_segments += len(segments)
            
            for segment in segments:
                if segment.get("type") != "activity":
                    skipped_no_activity += 1
                    continue
                
                name = segment.get("name", "").strip()
                if not name:
                    skipped_no_name += 1
                    logger.warning(f"Segment in day {day_idx} has no name, skipping: {segment}")
                    continue
                
                # Use name as key for deduplication
                name_lower = name.lower()
                if name_lower in seen_places:
                    skipped_duplicate += 1
                    logger.debug(f"Duplicate place skipped: {name}")
                    continue
                seen_places.add(name_lower)
                
                category = segment.get("category", "").lower() if segment.get("category") else ""
                address = segment.get("address", "")
                rating = segment.get("rating")
                votes = segment.get("votes") or segment.get("userRatingCount") or 0
                price_level = segment.get("price_level")
                estimated_cost_vnd = segment.get("estimated_cost_vnd", 0)
                description = segment.get("description", "")
                
                place_info = {
                    "name": name,
                    "address": address,
                    "rating": rating,
                    "votes": votes,
                    "price_level": price_level,
                    "estimated_cost_vnd": estimated_cost_vnd,
                    "description": description,
                    "category": category
                }
                
                if category == "food":
                    food_places.append(place_info)
                    added_places += 1
                elif category == "drink" or category == "coffee":
                    coffee_places.append(place_info)
                    added_places += 1
                else:
                    # All other categories are places/activities
                    places.append(place_info)
                    added_places += 1
        
        # Log statistics
        logger.info(f"Extracted places for description: {len(places)} places, {len(food_places)} food, {len(coffee_places)} coffee")
        logger.info(f"Statistics: {total_segments} total segments, {skipped_no_activity} skipped (not activity), {skipped_no_name} skipped (no name), {skipped_duplicate} skipped (duplicate), {added_places} added")
        
        # Build prompt for GPT to generate descriptions
        prompt = f"""
Bạn là TravelGPT. Hãy tạo mô tả lịch trình DU LỊCH bằng TIẾNG VIỆT theo ĐÚNG format dưới đây.

Thông tin:
- Thành phố: {city}
- Thời gian: {duration_days} ngày
- Ngân sách: {budget_range} VNĐ

Danh sách địa điểm từ itinerary (TỔNG CỘNG: {len(places) + len(food_places) + len(coffee_places)} địa điểm):

🏛 Địa điểm tham quan (Sightseeing / Activities) - {len(places)} địa điểm:
{json.dumps(places, ensure_ascii=False, indent=2)}

🍽 Quán ăn (Restaurants / Local Food) - {len(food_places)} địa điểm:
{json.dumps(food_places, ensure_ascii=False, indent=2)}

☕ Quán cà phê - {len(coffee_places)} địa điểm:
{json.dumps(coffee_places, ensure_ascii=False, indent=2)}

YÊU CẦU FORMAT (BẮT BUỘC phải tuân theo CHÍNH XÁC - TẤT CẢ PHẢI BẰNG TIẾNG VIỆT):

Thành phố: {city}
Thời gian: {duration_days} ngày
Ngân sách: {budget_range} VNĐ

Địa điểm tham quan
🏛 Địa điểm (Tham quan / Hoạt động)

[Tên địa điểm 1 - PHẢI hiển thị tên đầy đủ từ danh sách]

Mô tả: [1–2 câu mô tả ngắn gọn bằng tiếng Việt]

[Tên địa điểm 2 - PHẢI hiển thị tên đầy đủ từ danh sách]

Mô tả: [1–2 câu mô tả ngắn gọn bằng tiếng Việt]

VÍ DỤ CỤ THỂ (PHẢI tuân theo format này):
Cầu Vàng

Mô tả: Cầu Vàng nổi tiếng với thiết kế độc đáo, tạo cảm giác như đang đi giữa không trung, mang đến trải nghiệm tuyệt vời cho du khách.

Bảo tàng Mỹ thuật Đà Nẵng

Mô tả: Bảo tàng Mỹ thuật Đà Nẵng trưng bày nhiều tác phẩm nghệ thuật độc đáo, giúp du khách hiểu rõ hơn về văn hóa và nghệ thuật Việt Nam.

🍽 Quán ăn (Nhà hàng / Đồ ăn địa phương)

🍽 <b><Tên quán ăn></b>
⭐ <rating>/5 · <reviewCount> đánh giá
💵 <priceRange>  |  🍽️ Món nổi bật: <signature dish>
📍 <short address, if available>
Mô tả: <short, clear, local culinary description (1–2 sentences)>

🍽 <b><Tên quán ăn></b>
⭐ <rating>/5 · <reviewCount> đánh giá
💵 <priceRange>  |  🍽️ Món nổi bật: <signature dish>
📍 <short address, if available>
Mô tả: <short, clear, local culinary description (1–2 sentences)>

☕ Quán cà phê

☕ <b><Tên quán cà phê></b>
⭐ <rating>/5 · <reviewCount> đánh giá
💵 <priceRange>  |  🍰 Thức uống nổi bật: <signature drink>
📍 <short address, if available>
Mô tả: <short, clear, local description (1–2 sentences)>

☕ <b><Tên quán cà phê></b>
⭐ <rating>/5 · <reviewCount> đánh giá
💵 <priceRange>  |  🍰 Thức uống nổi bật: <signature drink>
📍 <short address, if available>
Mô tả: <short, clear, local description (1–2 sentences)>

Nhận xét về lịch trình

<Bất kỳ gợi ý ngắn hoặc tóm tắt bằng tiếng Việt>

QUAN TRỌNG:
- TẤT CẢ phải viết bằng TIẾNG VIỆT (tiêu đề, mô tả, nhận xét)
- PHẢI liệt kê và mô tả TẤT CẢ các địa điểm có trong danh sách trên - KHÔNG được bỏ sót bất kỳ địa điểm nào
- Mỗi địa điểm PHẢI có TÊN ĐẦY ĐỦ (lấy từ trường "name" trong danh sách) và mô tả ngắn gọn 1-2 câu bằng tiếng Việt
- TÊN ĐỊA ĐIỂM PHẢI được hiển thị TRƯỚC mô tả, trên một dòng riêng
- KHÔNG được bỏ qua tên địa điểm, chỉ hiển thị mô tả
- KHÔNG được thêm địa điểm không có trong danh sách
- KHÔNG được bỏ sót địa điểm nào trong danh sách
- KHÔNG được thêm hoặc bỏ bất kỳ section nào
- KHÔNG được thay đổi format (giữ nguyên emoji, tiêu đề, cấu trúc)

QUAN TRỌNG ĐẶC BIỆT CHO NHÀ HÀNG VÀ QUÁN CÀ PHÊ:
- Mỗi nhà hàng/quán cà phê PHẢI tuân theo format CHÍNH XÁC như trên
- Tên nhà hàng/quán cà phê PHẢI in đậm với <b><Tên></b> (HTML bold, KHÔNG dùng Markdown **...**)
- Mỗi nhà hàng bắt đầu với 🍽 và tên in đậm: 🍽 <b><Tên quán ăn></b>
- Mỗi quán cà phê bắt đầu với ☕ và tên in đậm: ☕ <b><Tên quán cà phê></b>
- Rating và số đánh giá: Sử dụng số liệu từ dữ liệu (rating, votes). Format: ⭐ <rating>/5 · <votes> đánh giá
- Price range: 
  * Nếu có price_level: ₫ (bình dân), ₫₫ (tầm trung), ₫₫₫ (cao cấp), ₫₫₫₫ (sang trọng)
  * HOẶC nếu có estimated_cost_vnd: Tính theo người (ví dụ: 100.000đ – 250.000đ/người)
- Signature dish/drink: PHẢI cụ thể, không được chung chung
  * ❌ KHÔNG được viết "món ngon đa dạng", "nhiều món", "đồ ăn ngon", "phục vụ tốt"
  * ✔ PHẢI viết cụ thể: "Phở bò tái chín, nước dùng trong và ngọt xương", "Cà phê trứng", "Cold Brew", "Hạt rang tại chỗ"
  * Signature dish phải được suy luận từ tên nhà hàng hoặc description có sẵn
  * Cho quán cà phê: Dùng "🍰 Thức uống nổi bật:" thay vì "Món nổi bật:"
- Address: Chỉ hiển thị nếu có trong dữ liệu, format ngắn gọn
- Mô tả: 1-2 câu ngắn gọn, rõ ràng, về ẩm thực địa phương, viết bằng tiếng Việt
- KHÔNG được sử dụng Markdown bold (**...**), CHỈ dùng HTML bold (<b>...</b>)

- Phần "Nhận xét về lịch trình" là phần cuối, viết 1-2 câu gợi ý hoặc tóm tắt bằng tiếng Việt
- Nếu một section không có địa điểm nào, vẫn phải giữ section đó với tiêu đề (nhưng không cần liệt kê)

YÊU CẦU CUỐI CÙNG - RẤT QUAN TRỌNG:
- Bạn PHẢI mô tả TẤT CẢ {len(places) + len(food_places) + len(coffee_places)} địa điểm trong danh sách trên
- Đếm lại số lượng địa điểm bạn đã mô tả: phải bằng {len(places)} địa điểm tham quan + {len(food_places)} quán ăn + {len(coffee_places)} quán cà phê = {len(places) + len(food_places) + len(coffee_places)} địa điểm
- KHÔNG được bỏ sót bất kỳ địa điểm nào trong danh sách
- Nếu bạn bỏ sót địa điểm, bạn đã làm sai yêu cầu
- ĐỐI VỚI ĐỊA ĐIỂM THAM QUAN: Mỗi địa điểm PHẢI có TÊN ĐẦY ĐỦ (từ trường "name" trong JSON) hiển thị TRƯỚC mô tả, trên một dòng riêng. KHÔNG được chỉ hiển thị mô tả mà bỏ qua tên.

Chỉ trả về văn bản theo đúng format trên bằng tiếng Việt, không thêm gì khác.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
        )

        content = response.choices[0].message.content
        if not content:
            return ""
        return content.strip()

    # -----------------------------
    # 5. Modify existing itinerary based on user request
    # -----------------------------
    async def modify_itinerary(self, previous_itinerary: dict, modification_request: str, parsed_data: dict, conversation_history: Optional[list] = None) -> dict:
        """
        Uses GPT to modify an existing itinerary based on user's modification request.
        Returns modified planner_request that can be used to regenerate itinerary.
        """
        # Build context from conversation history if available
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            history_context = "\n\nLịch sử cuộc trò chuyện trước đó:\n"
            # Use all messages in the conversation (up to 100 for very long sessions)
            messages_to_include = conversation_history[-100:] if len(conversation_history) > 100 else conversation_history
            for msg in messages_to_include:
                role = "Người dùng" if msg.get("role") == "user" else "TravelGPT"
                content = msg.get("content", "")
                history_context += f"- {role}: {content}\n"
        
        prompt = f"""
Bạn là AI Travel Planner tiếng Việt. Người dùng muốn chỉnh sửa lịch trình hiện tại.{history_context}

Lịch trình hiện tại:
{json.dumps(previous_itinerary, ensure_ascii=False, indent=2)}

Yêu cầu chỉnh sửa của người dùng:
---
{modification_request}
---

Dữ liệu đã parse từ yêu cầu:
{json.dumps(parsed_data, ensure_ascii=False, indent=2)}

Hãy trả về JSON với các thông tin đã được cập nhật từ lịch trình hiện tại và yêu cầu mới:

{{
  "budget_vnd": <ngân sách mới hoặc giữ nguyên từ previous_itinerary>,
  "energy": <mức năng lượng mới hoặc giữ nguyên>,
  "city": <thành phố, giữ nguyên từ previous_itinerary>,
  "duration_days": <số ngày mới hoặc giữ nguyên từ previous_itinerary>,
  "date_range": {{
      "start": <ngày bắt đầu mới hoặc giữ nguyên>,
      "end": <ngày kết thúc mới hoặc giữ nguyên>
  }},
  "preferences": {{
      "food": <sở thích món ăn mới hoặc giữ nguyên>,
      "activities": <loại hoạt động mới hoặc giữ nguyên>,
      "accommodation": <loại khách sạn mới hoặc giữ nguyên>,
      "style": <phong cách mới hoặc giữ nguyên>
  }}
}}

QUAN TRỌNG:
- BẮT BUỘC phải trả về TẤT CẢ các field trong JSON schema trên, KHÔNG được bỏ sót field nào.
- Nếu người dùng chỉ muốn thay đổi một phần (ví dụ: chỉ số ngày), giữ nguyên các thông tin khác từ previous_itinerary.
- Nếu parsed_data có thông tin mới (không phải null), ưu tiên sử dụng thông tin mới từ parsed_data.
- Nếu parsed_data không có thông tin về một field (null hoặc không có), giữ nguyên từ previous_itinerary.
- Nếu người dùng nói số ngày mới (ví dụ: "5 ngày 4 đêm", "tôi muốn 5 ngày", "tôi muốn lịch 4 ngày 3 đêm"), 
  BẮT BUỘC phải extract số ngày đầu tiên và đặt vào duration_days (ví dụ: "4 ngày 3 đêm" -> 4).
- Nếu modification_type là "duration", BẮT BUỘC phải extract duration_days từ yêu cầu chỉnh sửa và cập nhật vào JSON.
- Về city: Nếu người dùng không đề cập địa điểm mới trong yêu cầu chỉnh sửa, GIỮ NGUYÊN city từ previous_itinerary.
- Về budget_vnd: Nếu người dùng không đề cập ngân sách mới trong yêu cầu chỉnh sửa, GIỮ NGUYÊN budget_vnd từ previous_itinerary.
- Về date_range: Nếu người dùng chỉ thay đổi số ngày (duration_days), tính lại end date dựa trên start date và duration_days mới.
- Luôn đảm bảo JSON trả về có đầy đủ tất cả các field, không được để null trừ khi thực sự không có thông tin.

Chỉ trả JSON, không giải thích.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1,
        )

        try:
            content = response.choices[0].message.content
            if not content:
                return {}
            return json.loads(content)
        except Exception:
            return {}

    # -----------------------------
    # 4.5. Generate formatted restaurant/coffee list
    # -----------------------------
    async def generate_formatted_list(self, list_category: str, city: str, limit: int = 10) -> str:
        """
        Generate a formatted list of restaurants or coffee shops with the new format.
        Uses PlaceService to fetch real data and formats it according to the new requirements.
        """
        from app.services.place_service import PlaceService
        
        place_service = PlaceService()
        
        if list_category == "restaurant":
            places = place_service.search_top_food(city, limit=limit)
            category_name = "Quán ăn"
            category_emoji = "🍽"
            signature_label = "🍽️ Món nổi bật"
        elif list_category == "drink" or list_category == "coffee":
            places = place_service.search_top_drink(city, limit=limit)
            category_name = "Quán đồ uống"
            category_emoji = "🥤"
            signature_label = "🍰 Thức uống nổi bật"
        else:
            return f"Không hỗ trợ danh sách loại: {list_category}"
        
        if not places:
            return f"Không tìm thấy {category_name.lower()} nào tại {city}."
        
        # Format places according to new format
        formatted_list = f"Dưới đây là một số {category_name.lower()} tại {city} mà bạn có thể tham khảo:\n\n"
        
        for place in places[:limit]:
            name = place.get("name", "")
            rating = place.get("rating", 0)
            votes = place.get("votes", 0) or place.get("userRatingCount", 0)
            price_level = place.get("price_level")
            estimated_cost_vnd = place.get("estimated_cost_vnd", 0)
            address = place.get("address", "")
            description = place.get("description", "")
            
            # Format price range
            price_range = ""
            if price_level is not None:
                price_symbols = {0: "₫", 1: "₫₫", 2: "₫₫₫", 3: "₫₫₫₫", 4: "₫₫₫₫"}
                price_range = price_symbols.get(price_level, "₫")
            elif estimated_cost_vnd > 0:
                # Calculate per person estimate (divide by 2 for 2 people, or use a reasonable estimate)
                per_person = estimated_cost_vnd // 2
                if per_person < 100000:
                    price_range = f"{per_person:,.0f}đ/người".replace(",", ".")
                else:
                    price_range = f"{per_person//1000:.0f}kđ/người"
            
            # Extract signature dish from description or infer from name
            signature_dish = ""
            name_lower = name.lower()
            if "phở" in name_lower:
                signature_dish = "Phở bò tái chín, nước dùng trong và ngọt xương"
            elif "bún chả" in name_lower:
                signature_dish = "Bún chả truyền thống, thịt nướng thơm lừng"
            elif "bún bò" in name_lower:
                signature_dish = "Bún bò Huế, nước dùng cay nồng"
            elif "chả cá" in name_lower:
                signature_dish = "Chả cá Lã Vọng, cá nướng thơm và nghệ tươi"
            elif "lẩu" in name_lower:
                signature_dish = "Lẩu nóng hổi, nước dùng đậm đà"
            elif "bánh mì" in name_lower or "banh mi" in name_lower:
                signature_dish = "Bánh mì giòn tan, nhân đầy đặn"
            elif list_category == "drink" or list_category == "coffee":
                if "trứng" in name_lower:
                    signature_dish = "Cà phê trứng béo ngậy"
                elif "specialty" in name_lower or "roastery" in name_lower:
                    signature_dish = "Cà phê specialty, hạt rang tại chỗ"
                else:
                    signature_dish = "Cà phê đậm đà, pha chế chuyên nghiệp"
            else:
                # Try to extract from description
                if description:
                    # Look for dish mentions in description
                    if "phở" in description.lower():
                        signature_dish = "Phở truyền thống"
                    elif "bún" in description.lower():
                        signature_dish = "Bún đặc biệt"
                    else:
                        signature_dish = "Món địa phương đặc trưng"
                else:
                    signature_dish = "Món địa phương đặc trưng"
            
            # Format rating and votes
            rating_str = f"{rating:.1f}" if rating else "0"
            votes_str = f"{votes:,}".replace(",", ".") if votes else "0"
            
            # Build formatted entry
            formatted_list += f"{category_emoji}{name}\n"
            formatted_list += f"⭐ {rating_str}/5 · {votes_str} đánh giá\n"
            
            if price_range:
                formatted_list += f"💵 {price_range}  |  {signature_label}: {signature_dish}\n"
            else:
                formatted_list += f"{signature_label}: {signature_dish}\n"
            
            if address:
                # Shorten address if too long
                short_address = address
                if len(address) > 60:
                    # Try to extract street name and district
                    parts = address.split(",")
                    if len(parts) >= 2:
                        short_address = ",".join(parts[:2]).strip()
                formatted_list += f"📍 {short_address}\n"
            
            # Use description if available, otherwise create a simple one
            if description:
                # Ensure description is max 2 sentences
                sentences = description.split(".")
                if len(sentences) > 2:
                    description = ". ".join(sentences[:2]).strip()
                    if not description.endswith("."):
                        description += "."
                formatted_list += f"Mô tả: {description}\n"
            else:
                formatted_list += f"Mô tả: {category_name} nổi tiếng tại {city}, được đánh giá cao bởi khách hàng.\n"
            
            formatted_list += "\n"
        
        return formatted_list.strip()

    # -----------------------------
    # 5. Generate chat response for conversation
    # -----------------------------
    async def generate_chat_response(self, message: str, conversation_history: Optional[list] = None) -> str:
        """
        Uses GPT to generate natural conversation response in Vietnamese.
        This allows the agent to chat with users before creating plans.
        Model: gpt-4o-mini (có thể nâng cấp lên gpt-4o để tốt hơn)
        """
        # Build system message with instructions
        system_message = """Bạn là một travel itinerary assistant.
Tuân thủ các quy tắc sau cho mọi phản hồi.

1️⃣ INPUT CHECKING & CONFIRMATION FLOW

Sau khi người dùng cung cấp yêu cầu:

Extract:
- City (Thành phố)
- Duration (Thời gian - số ngày)
- Budget (Ngân sách - min & max)

Nếu budget bị thiếu:
- Set:
  Budget Min = budget_min trong user profile
  Budget Max = budget_max trong user profile
- Hỏi:
  "Bạn có muốn cung cấp ngân sách dự kiến (theo số tiền) không? Nếu có, hãy cho mình biết ngân sách tối thiểu và tối đa nhé."

Sau đó xác nhận cả 3 mục trước khi lập kế hoạch:
- Thành phố
- Thời gian
- Ngân sách

Nếu cả 3 giá trị đều tồn tại, xác nhận ngay:
"Mình sẽ lập kế hoạch cho chuyến đi:
Thành phố: …
Thời gian: …
Ngân sách: …
Bạn xác nhận chứ?"

CHỈ tiếp tục với itinerary sau khi người dùng xác nhận.

⚠️ QUAN TRỌNG - Xử lý câu hỏi follow-up và câu trả lời xác nhận:

1. **Nhận biết câu trả lời xác nhận**: Nếu người dùng trả lời "có", "yes", "ok", "đúng", "đồng ý", "tiếp tục" hoặc các từ tương tự, bạn PHẢI:
   - Xem lại câu hỏi/câu đề xuất CUỐI CÙNG của bạn trong lịch sử cuộc trò chuyện
   - Hiểu rõ người dùng đang xác nhận điều gì
   - Nếu là xác nhận cho việc lập kế hoạch, hãy xác nhận lại thông tin và báo rằng bạn sẽ tạo itinerary

2. **Xử lý câu hỏi follow-up**: Nếu người dùng hỏi thêm về một chủ đề đã được đề cập trước đó:
   - Xem lại ngữ cảnh trong lịch sử cuộc trò chuyện
   - Trả lời dựa trên thông tin đã có trong cuộc trò chuyện
   - Nếu cần thông tin mới, hãy hỏi cụ thể

3. **Nguyên tắc chung**:
   - Luôn đọc kỹ lịch sử cuộc trò chuyện để hiểu ngữ cảnh
   - Trả lời một cách tự nhiên, thân thiện và hữu ích
   - Nếu không chắc chắn về ngữ cảnh, hãy hỏi lại một cách cụ thể"""

        # Build messages array with conversation history
        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history to messages (all messages in session, up to 100 for very long sessions)
        if conversation_history and len(conversation_history) > 0:
            # Use all messages in the conversation (up to 100 for very long sessions)
            messages_to_include = conversation_history[-100:] if len(conversation_history) > 100 else conversation_history
            for msg in messages_to_include:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Map "assistant" to "assistant" role for OpenAI API
                if role == "assistant":
                    messages.append({"role": "assistant", "content": content})
                else:
                    messages.append({"role": "user", "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Có thể nâng cấp lên gpt-4o để hiểu user tốt hơn
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )

        content = response.choices[0].message.content
        if not content:
            return "Xin lỗi, tôi không hiểu. Bạn có thể nói rõ hơn được không?"
        return content.strip()

    # -----------------------------
    # 6.6. Generate explanation for why a city matches user preferences
    # -----------------------------
    def generate_city_explanation(self, city: str, city_characteristics: dict, user_preferences: list) -> str:
        """
        Generate a brief explanation of why a city matches user preferences.
        Returns a short sentence explaining the match.
        """
        if not user_preferences or len(user_preferences) == 0:
            return "Thành phố nổi tiếng với nhiều điểm tham quan thú vị"
        
        user_prefs_lower = [pref.lower() for pref in user_preferences]
        matched_features = []
        
        # City-specific descriptions based on preferences
        city_descriptions = {
            "Nha Trang": {
                "photography": "bãi biển dài với nước trong xanh, hoàn hảo cho chụp ảnh",
                "coffee": "nhiều quán cà phê view biển và không gian đẹp",
                "nightlife": "đời sống về đêm sôi động với nhiều bar và club",
                "food": "hải sản tươi sống và ẩm thực địa phương đa dạng",
                "adventure": "lặn biển, chèo thuyền kayak và các hoạt động thể thao nước"
            },
            "Đà Nẵng": {
                "photography": "cầu Vàng nổi tiếng và cảnh quan đô thị hiện đại",
                "coffee": "văn hóa cà phê phong phú với nhiều quán độc đáo",
                "nightlife": "nhiều quán bar, pub và khu vui chơi về đêm",
                "food": "ẩm thực đa dạng từ street food đến nhà hàng cao cấp",
                "adventure": "nhiều hoạt động mạo hiểm như zipline, leo núi"
            },
            "Hội An": {
                "photography": "phố cổ cổ kính với đèn lồng đầy màu sắc, thiên đường cho nhiếp ảnh",
                "coffee": "nhiều quán cà phê cổ kính và không gian lãng mạn",
                "nightlife": "đời sống về đêm nhẹ nhàng với bar và nhà hàng",
                "food": "ẩm thực địa phương nổi tiếng như cao lầu, bánh mì Phượng",
                "culture": "di sản văn hóa UNESCO với kiến trúc cổ độc đáo"
            },
            "Phú Quốc": {
                "photography": "bãi biển hoang sơ và cảnh quan thiên nhiên tuyệt đẹp",
                "coffee": "quán cà phê view biển và không gian yên tĩnh",
                "nightlife": "resort và bar trên biển với không gian sang trọng",
                "food": "hải sản tươi ngon và nhà hàng cao cấp",
                "luxury": "nhiều resort 5 sao và dịch vụ spa cao cấp"
            },
            "Vũng Tàu": {
                "photography": "bãi biển đẹp và tượng Chúa Kitô Vua",
                "coffee": "nhiều quán cà phê ven biển",
                "food": "hải sản giá rẻ và ẩm thực địa phương",
                "budget": "phù hợp với ngân sách, giá cả hợp lý"
            },
            "Quy Nhơn": {
                "photography": "bãi biển hoang sơ và cảnh quan thiên nhiên",
                "coffee": "quán cà phê địa phương với không gian yên tĩnh",
                "food": "ẩm thực miền Trung đặc sắc",
                "nature": "thiên nhiên hoang sơ và bãi biển ít người"
            },
            "Đà Lạt": {
                "photography": "phong cảnh núi non, đồi thông và kiến trúc Pháp cổ",
                "coffee": "văn hóa cà phê nổi tiếng với nhiều quán độc đáo",
                "nature": "khí hậu mát mẻ và cảnh quan thiên nhiên tuyệt đẹp",
                "romantic": "không gian lãng mạn với đồi thông và hồ",
                "adventure": "leo núi, trekking và các hoạt động ngoài trời"
            },
            "Sapa": {
                "photography": "ruộng bậc thang và cảnh quan núi non hùng vĩ",
                "nature": "thiên nhiên hoang sơ và khí hậu mát mẻ",
                "adventure": "trekking và leo núi Fansipan",
                "culture": "văn hóa các dân tộc thiểu số độc đáo"
            },
            "Hà Nội": {
                "photography": "phố cổ với kiến trúc cổ kính và nhà thờ cổ",
                "coffee": "văn hóa cà phê trứng và cà phê vỉa hè nổi tiếng",
                "nightlife": "nhiều bar, pub và khu vui chơi về đêm",
                "food": "ẩm thực đường phố đa dạng và nổi tiếng",
                "culture": "di sản văn hóa với nhiều bảo tàng và di tích"
            },
            "Hồ Chí Minh": {
                "photography": "kiến trúc đô thị hiện đại và các tòa nhà cổ",
                "coffee": "văn hóa cà phê đa dạng từ truyền thống đến hiện đại",
                "nightlife": "đời sống về đêm sôi động nhất Việt Nam",
                "food": "ẩm thực đa dạng từ street food đến nhà hàng cao cấp",
                "shopping": "nhiều trung tâm mua sắm và chợ đêm"
            },
            "Huế": {
                "photography": "cố đô với kiến trúc cổ kính và lăng tẩm",
                "culture": "di sản văn hóa UNESCO với nhiều di tích lịch sử",
                "food": "ẩm thực cung đình và món ăn địa phương đặc sắc",
                "historical": "lịch sử phong phú với nhiều di tích cổ"
            }
        }
        
        # Get city-specific descriptions
        city_desc = city_descriptions.get(city, {})
        
        # Build explanation based on user preferences
        explanations = []
        for pref in user_prefs_lower[:3]:  # Use first 3 preferences
            if pref in city_desc:
                explanations.append(city_desc[pref])
            elif "photo" in pref and "photography" in city_desc:
                explanations.append(city_desc["photography"])
            elif "cà phê" in pref or "coffee" in pref:
                if "coffee" in city_desc:
                    explanations.append(city_desc["coffee"])
                elif city_characteristics.get("food"):
                    explanations.append("nhiều quán cà phê đặc sắc")
            elif "đêm" in pref or "nightlife" in pref:
                if "nightlife" in city_desc:
                    explanations.append(city_desc["nightlife"])
                elif city_characteristics.get("nightlife"):
                    explanations.append("đời sống về đêm sôi động")
            elif "ăn" in pref or "food" in pref:
                if "food" in city_desc:
                    explanations.append(city_desc["food"])
                elif city_characteristics.get("food"):
                    explanations.append("ẩm thực đa dạng và ngon")
            elif "phiêu lưu" in pref or "adventure" in pref:
                if "adventure" in city_desc:
                    explanations.append(city_desc["adventure"])
                elif city_characteristics.get("adventure"):
                    explanations.append("nhiều hoạt động mạo hiểm")
            elif "lãng mạn" in pref or "romantic" in pref:
                if "romantic" in city_desc:
                    explanations.append(city_desc["romantic"])
                elif city_characteristics.get("romantic"):
                    explanations.append("không gian lãng mạn")
            elif "văn hóa" in pref or "culture" in pref:
                if "culture" in city_desc:
                    explanations.append(city_desc["culture"])
                elif city_characteristics.get("culture"):
                    explanations.append("văn hóa đậm đà")
            elif "thiên nhiên" in pref or "nature" in pref:
                if "nature" in city_desc:
                    explanations.append(city_desc["nature"])
                elif city_characteristics.get("nature"):
                    explanations.append("thiên nhiên hoang sơ")
            elif "sang trọng" in pref or "luxury" in pref:
                if "luxury" in city_desc:
                    explanations.append(city_desc["luxury"])
                elif city_characteristics.get("luxury"):
                    explanations.append("resort và dịch vụ cao cấp")
            elif "tiết kiệm" in pref or "budget" in pref:
                if "budget" in city_desc:
                    explanations.append(city_desc["budget"])
                elif city_characteristics.get("budget"):
                    explanations.append("phù hợp với ngân sách")
        
        # If we have explanations, join them
        if explanations:
            # Take unique explanations (max 2-3)
            unique_explanations = []
            seen = set()
            for exp in explanations:
                if exp not in seen:
                    unique_explanations.append(exp)
                    seen.add(exp)
                    if len(unique_explanations) >= 2:
                        break
            
            return ", ".join(unique_explanations)
        else:
            # Fallback: generic description based on city characteristics
            if city_characteristics.get("beach"):
                return "bãi biển đẹp và nhiều hoạt động giải trí"
            elif city_characteristics.get("mountain"):
                return "phong cảnh núi non hùng vĩ và không khí trong lành"
            elif city_characteristics.get("historical"):
                return "di tích lịch sử và văn hóa đậm đà"
            elif city_characteristics.get("city"):
                return "thành phố sôi động với nhiều điểm tham quan"
            else:
                return "thành phố nổi tiếng với nhiều điểm tham quan thú vị"

    # -----------------------------
    # 6.5. Suggest cities based on location type and user preferences
    # -----------------------------
    def suggest_cities_by_location_type(self, location_type: str, user_preferences: Optional[list] = None) -> list:
        """
        Suggest Vietnamese cities based on location type and user preferences.
        Returns a ranked list of city names that match the location type and user preferences.
        
        Args:
            location_type: Type of location (beach, mountain, city, nature, historical)
            user_preferences: List of user preferences from profile (e.g., ["food", "nature", "adventure"])
        
        Returns:
            List of city names ranked by relevance to user preferences
        """
        # City characteristics mapping (for preference matching)
        city_characteristics = {
            "Nha Trang": {
                "beach": True,
                "food": True,
                "adventure": True,
                "nightlife": True,
                "family": True,
                "luxury": True
            },
            "Phú Quốc": {
                "beach": True,
                "nature": True,
                "luxury": True,
                "romantic": True,
                "family": True,
                "food": True
            },
            "Đà Nẵng": {
                "beach": True,
                "city": True,
                "food": True,
                "adventure": True,
                "family": True,
                "nightlife": True
            },
            "Vũng Tàu": {
                "beach": True,
                "food": True,
                "family": True,
                "budget": True
            },
            "Mũi Né": {
                "beach": True,
                "adventure": True,
                "nature": True,
                "romantic": True
            },
            "Cửa Lò": {
                "beach": True,
                "family": True,
                "budget": True
            },
            "Quy Nhơn": {
                "beach": True,
                "food": True,
                "nature": True,
                "budget": True
            },
            "Hội An": {
                "beach": True,
                "city": True,
                "historical": True,
                "food": True,
                "romantic": True,
                "culture": True
            },
            "Đà Lạt": {
                "mountain": True,
                "nature": True,
                "romantic": True,
                "food": True,
                "adventure": True,
                "culture": True
            },
            "Sapa": {
                "mountain": True,
                "nature": True,
                "adventure": True,
                "culture": True,
                "trekking": True
            },
            "Mai Châu": {
                "mountain": True,
                "nature": True,
                "culture": True,
                "budget": True
            },
            "Mộc Châu": {
                "mountain": True,
                "nature": True,
                "culture": True
            },
            "Yên Bái": {
                "mountain": True,
                "nature": True,
                "culture": True
            },
            "Lào Cai": {
                "mountain": True,
                "nature": True,
                "culture": True,
                "adventure": True
            },
            "Hà Nội": {
                "city": True,
                "historical": True,
                "food": True,
                "culture": True,
                "nightlife": True
            },
            "Hồ Chí Minh": {
                "city": True,
                "food": True,
                "nightlife": True,
                "shopping": True,
                "culture": True
            },
            "Huế": {
                "city": True,
                "historical": True,
                "culture": True,
                "food": True
            },
            "Cát Bà": {
                "nature": True,
                "beach": True,
                "adventure": True
            },
            "Bà Nà": {
                "nature": True,
                "mountain": True,
                "adventure": True,
                "family": True
            },
            "Tam Đảo": {
                "nature": True,
                "mountain": True,
                "romantic": True
            },
            "Mỹ Sơn": {
                "historical": True,
                "culture": True
            },
            "Cố Đô Hoa Lư": {
                "historical": True,
                "culture": True
            }
        }
        
        # Base city suggestions by location type
        city_suggestions = {
            "beach": [
                "Nha Trang",
                "Phú Quốc",
                "Đà Nẵng",
                "Vũng Tàu",
                "Mũi Né",
                "Cửa Lò",
                "Quy Nhơn",
                "Hội An"
            ],
            "mountain": [
                "Đà Lạt",
                "Sapa",
                "Mai Châu",
                "Mộc Châu",
                "Yên Bái",
                "Lào Cai"
            ],
            "city": [
                "Hà Nội",
                "Hồ Chí Minh",
                "Đà Nẵng",
                "Huế",
                "Hội An",
                "Nha Trang"
            ],
            "nature": [
                "Đà Lạt",
                "Sapa",
                "Phú Quốc",
                "Cát Bà",
                "Bà Nà",
                "Tam Đảo"
            ],
            "historical": [
                "Huế",
                "Hội An",
                "Hà Nội",
                "Mỹ Sơn",
                "Cố Đô Hoa Lư"
            ]
        }
        
        base_cities = city_suggestions.get(location_type, [])
        
        # If no user preferences, return base list
        if not user_preferences or len(user_preferences) == 0:
            return base_cities
        
        # Normalize preferences to lowercase for matching
        user_prefs_lower = [pref.lower() for pref in user_preferences]
        
        # Score cities based on how many preferences they match
        city_scores = {}
        for city in base_cities:
            if city not in city_characteristics:
                city_scores[city] = 0
                continue
            
            characteristics = city_characteristics[city]
            score = 0
            
            # Check each user preference against city characteristics
            for pref in user_prefs_lower:
                # Direct match
                if pref in characteristics and characteristics[pref]:
                    score += 2
                # Partial matches (e.g., "food" matches "food", "coffee" matches "food")
                elif pref == "food" and (characteristics.get("food") or characteristics.get("restaurant")):
                    score += 2
                elif pref == "coffee" and characteristics.get("food"):
                    score += 1
                elif pref == "adventure" and (characteristics.get("adventure") or characteristics.get("trekking")):
                    score += 2
                elif pref == "nature" and characteristics.get("nature"):
                    score += 2
                elif pref == "culture" and characteristics.get("culture"):
                    score += 2
                elif pref == "romantic" and characteristics.get("romantic"):
                    score += 2
                elif pref == "budget" and characteristics.get("budget"):
                    score += 1
                elif pref == "luxury" and characteristics.get("luxury"):
                    score += 1
            
            city_scores[city] = score
        
        # Sort cities by score (descending), then by original order if scores are equal
        sorted_cities = sorted(
            base_cities,
            key=lambda city: (city_scores.get(city, 0), -base_cities.index(city)),
            reverse=True
        )
        
        logger.info(f"City suggestions for location_type={location_type}, preferences={user_preferences}: {sorted_cities[:6]} (scores: {[(c, city_scores.get(c, 0)) for c in sorted_cities[:6]]})")
        
        return sorted_cities

    # -----------------------------
    # 6. Generate confirmation message with collected information
    # -----------------------------
    async def generate_confirmation_message(self, parsed_data: dict, conversation_history: Optional[list] = None, user_profile: Optional[dict] = None) -> str:
        """
        Generates a confirmation message asking user to confirm collected information before creating plan.
        Always confirms 3 items: City, Duration, Budget.
        If location_type is provided but city is missing, suggests cities based on location type.
        """
        # Extract key information
        city = parsed_data.get("city")
        location_type = parsed_data.get("location_type")
        budget_vnd = parsed_data.get("budget_vnd")
        duration_days = parsed_data.get("duration_days")
        budget_min = parsed_data.get("budget_min")
        budget_max = parsed_data.get("budget_max")
        
        # If budget is missing, try to get from user profile
        if (budget_vnd is None or budget_vnd <= 0) and user_profile:
            budget_min = user_profile.get("budget_min")
            budget_max = user_profile.get("budget_max")
        
        # Special case: If location_type is provided but city is missing, suggest cities
        if not city and location_type:
            # Extract user preferences from user_profile
            user_preferences = []
            if user_profile and user_profile.get("preferences_json"):
                try:
                    if isinstance(user_profile["preferences_json"], str):
                        user_preferences = json.loads(user_profile["preferences_json"])
                    elif isinstance(user_profile["preferences_json"], list):
                        user_preferences = user_profile["preferences_json"]
                except:
                    user_preferences = []
            
            # Get suggested cities based on location type and user preferences
            suggested_cities = self.suggest_cities_by_location_type(location_type, user_preferences)
            if suggested_cities:
                # Format city suggestions
                location_type_names = {
                    "beach": "biển",
                    "mountain": "núi",
                    "city": "thành phố",
                    "nature": "thiên nhiên",
                    "historical": "lịch sử"
                }
                location_name = location_type_names.get(location_type, location_type)
                
                message = f"Mình hiểu bạn muốn đi {location_name}!"
                
                # Mention preferences if available
                if user_preferences:
                    prefs_display = ", ".join(user_preferences[:3])  # Show first 3 preferences
                    message += f" Dựa trên sở thích của bạn ({prefs_display}),"
                
                message += "\n\nDưới đây là một số thành phố phù hợp ở Việt Nam:\n\n"
                
                # Get city characteristics for explanations
                city_characteristics_map = {
                    "Nha Trang": {
                        "beach": True,
                        "food": True,
                        "adventure": True,
                        "nightlife": True,
                        "family": True,
                        "luxury": True
                    },
                    "Phú Quốc": {
                        "beach": True,
                        "nature": True,
                        "luxury": True,
                        "romantic": True,
                        "family": True,
                        "food": True
                    },
                    "Đà Nẵng": {
                        "beach": True,
                        "city": True,
                        "food": True,
                        "adventure": True,
                        "family": True,
                        "nightlife": True
                    },
                    "Vũng Tàu": {
                        "beach": True,
                        "food": True,
                        "family": True,
                        "budget": True
                    },
                    "Mũi Né": {
                        "beach": True,
                        "adventure": True,
                        "nature": True,
                        "romantic": True
                    },
                    "Cửa Lò": {
                        "beach": True,
                        "family": True,
                        "budget": True
                    },
                    "Quy Nhơn": {
                        "beach": True,
                        "food": True,
                        "nature": True,
                        "budget": True
                    },
                    "Hội An": {
                        "beach": True,
                        "city": True,
                        "historical": True,
                        "food": True,
                        "romantic": True,
                        "culture": True
                    },
                    "Đà Lạt": {
                        "mountain": True,
                        "nature": True,
                        "romantic": True,
                        "food": True,
                        "adventure": True,
                        "culture": True
                    },
                    "Sapa": {
                        "mountain": True,
                        "nature": True,
                        "adventure": True,
                        "culture": True,
                        "trekking": True
                    },
                    "Mai Châu": {
                        "mountain": True,
                        "nature": True,
                        "culture": True,
                        "budget": True
                    },
                    "Mộc Châu": {
                        "mountain": True,
                        "nature": True,
                        "culture": True
                    },
                    "Yên Bái": {
                        "mountain": True,
                        "nature": True,
                        "culture": True
                    },
                    "Lào Cai": {
                        "mountain": True,
                        "nature": True,
                        "culture": True,
                        "adventure": True
                    },
                    "Hà Nội": {
                        "city": True,
                        "historical": True,
                        "food": True,
                        "culture": True,
                        "nightlife": True
                    },
                    "Hồ Chí Minh": {
                        "city": True,
                        "food": True,
                        "nightlife": True,
                        "shopping": True,
                        "culture": True
                    },
                    "Huế": {
                        "city": True,
                        "historical": True,
                        "culture": True,
                        "food": True
                    },
                    "Cát Bà": {
                        "nature": True,
                        "beach": True,
                        "adventure": True
                    },
                    "Bà Nà": {
                        "nature": True,
                        "mountain": True,
                        "adventure": True,
                        "family": True
                    },
                    "Tam Đảo": {
                        "nature": True,
                        "mountain": True,
                        "romantic": True
                    },
                    "Mỹ Sơn": {
                        "historical": True,
                        "culture": True
                    },
                    "Cố Đô Hoa Lư": {
                        "historical": True,
                        "culture": True
                    }
                }
                
                # Display cities with explanations
                for idx, suggested_city in enumerate(suggested_cities[:6], 1):  # Show max 6 cities
                    city_chars = city_characteristics_map.get(suggested_city, {})
                    explanation = self.generate_city_explanation(suggested_city, city_chars, user_preferences)
                    message += f"{idx}. **{suggested_city}**\n"
                    message += f"   💡 {explanation}\n\n"
                
                message += "Bạn muốn chọn thành phố nào? Vui lòng cho mình biết:\n"
                message += "- Tên thành phố bạn muốn đi\n"
                if not duration_days:
                    message += "- Số ngày bạn muốn đi (ví dụ: 3 ngày, 4 ngày 3 đêm)\n"
                if not budget_vnd and not (budget_min and budget_max):
                    message += "- Ngân sách dự kiến (nếu có)\n"
                
                return message
        
        # If budget is still missing, ask user
        if (budget_vnd is None or budget_vnd <= 0) and (budget_min is None or budget_max is None):
            return "Bạn có muốn cung cấp ngân sách dự kiến (theo số tiền) không? Nếu có, hãy cho mình biết ngân sách tối thiểu và tối đa nhé."
        
        # If we have all 3 values, confirm immediately
        if city and duration_days and (budget_vnd or (budget_min and budget_max)):
            # Format budget display
            if budget_vnd:
                budget_display = f"{budget_vnd:,}".replace(",", ".")
            elif budget_min and budget_max:
                budget_display = f"{budget_min:,} - {budget_max:,}".replace(",", ".")
            else:
                budget_display = "Chưa xác định"
            
            # Format duration display
            duration_display = f"{duration_days} ngày"
            if duration_days > 1:
                duration_display += f" ({duration_days - 1} đêm)"
            
            message = "Mình sẽ lập kế hoạch cho chuyến đi:\n"
            message += f"Thành phố: {city}\n"
            message += f"Thời gian: {duration_display}\n"
            message += f"Ngân sách: {budget_display} VNĐ\n"
            message += "\nBạn xác nhận chứ?"
            return message
        
        # If missing any of the 3 required items, ask for them
        missing_items = []
        if not city:
            missing_items.append("Thành phố")
        if not duration_days:
            missing_items.append("Thời gian")
        if not budget_vnd and not (budget_min and budget_max):
            missing_items.append("Ngân sách")
        
        message = "Mình cần thêm một số thông tin để tạo lịch trình cho bạn:\n"
        for item in missing_items:
            message += f"- {item}\n"
        message += "\nBạn có thể cung cấp các thông tin này không?"
        
        return message

    # -----------------------------
    # 7. Generate clarification message for ambiguous requests
    # -----------------------------
    async def generate_clarification_message(self, message: str, parsed_data: dict, conversation_history: Optional[list] = None, previous_itinerary: Optional[dict] = None) -> str:
        """
        Generates a clarification message when user's request is ambiguous.
        For example, if user just says "4 ngày" without context.
        """
        # Build context from conversation history if available
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            history_context = "\n\nLịch sử cuộc trò chuyện trước đó:\n"
            # Use all messages in the conversation (up to 100 for very long sessions)
            messages_to_include = conversation_history[-100:] if len(conversation_history) > 100 else conversation_history
            for msg in messages_to_include:
                role = "Người dùng" if msg.get("role") == "user" else "TravelGPT"
                content = msg.get("content", "")
                history_context += f"- {role}: {content}\n"

        # Check what information we have
        city = parsed_data.get("city")
        budget_vnd = parsed_data.get("budget_vnd")
        duration_days = parsed_data.get("duration_days")
        is_modification = parsed_data.get("is_modification", False)
        
        # Build clarification prompt
        clarification_prompt = f"""Bạn là TravelGPT, một AI travel planner thân thiện bằng tiếng Việt.{history_context}

Người dùng vừa nói:
---
{message}
---

Thông tin đã extract được:
- Địa điểm: {city if city else "chưa có"}
- Ngân sách: {budget_vnd if budget_vnd else "chưa có"}
- Số ngày: {duration_days if duration_days else "chưa có"}
- Có phải modification request: {is_modification}
- Có lịch trình trước đó: {"có" if previous_itinerary else "không"}

Hãy phân tích và hỏi lại người dùng để làm rõ ý định của họ. Nếu message quá ngắn hoặc không rõ ràng, hãy hỏi:
1. Nếu chỉ có số ngày (ví dụ: "4 ngày") mà không có địa điểm:
   - Hỏi xem họ muốn đi đâu
   - Hỏi xem họ muốn thay đổi lịch trình hiện tại hay tạo mới
2. Nếu có lịch trình trước đó và user chỉ nói số ngày:
   - Hỏi xem họ muốn thay đổi lịch trình hiện tại thành số ngày đó không
3. Nếu thiếu thông tin quan trọng:
   - Hỏi về địa điểm, ngân sách, hoặc số ngày tùy theo thông tin còn thiếu

Hãy trả lời một cách tự nhiên, thân thiện, và cụ thể. Chỉ trả về câu hỏi/clarification bằng tiếng Việt."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là TravelGPT, một AI travel planner chuyên nghiệp và thân thiện bằng tiếng Việt. Bạn luôn hỏi lại để làm rõ ý định của người dùng khi message không rõ ràng."},
                {"role": "user", "content": clarification_prompt}
            ],
            max_tokens=300,
            temperature=0.7,
        )

        content = response.choices[0].message.content
        if not content:
            return "Mình cần thêm thông tin để giúp bạn. Bạn có thể cho mình biết bạn muốn đi đâu và ngân sách dự kiến không?"
        return content.strip()

    # -----------------------------
    # 8. Detect Add Food Mode
    # -----------------------------
    def detect_add_food_mode(self, message: str) -> bool:
        """
        Detect if user wants to add restaurants to a specific day.
        Trigger keywords: "thêm quán ăn", "thêm nhà hàng", "more food/restaurant" + "ngày X"
        Do NOT trigger trip planning mode here.
        Do NOT ask for confirmation again.
        Do NOT regenerate whole itinerary.
        """
        message_lower = message.lower()
        
        # Check for food-related keywords (expanded list)
        food_keywords = [
            "thêm quán ăn", "thêm nhà hàng", "more food", "more restaurant",
            "thêm restaurant", "thêm food", "thêm quán", 
            "cho thêm quán", "cho thêm nhà hàng", "thêm món ăn", "thêm đồ ăn",
            "add restaurant", "add food", "add more food", "add more restaurant"
        ]
        has_food_keyword = any(keyword in message_lower for keyword in food_keywords)
        
        # Check for day specification (expanded patterns)
        # Also check for standalone "ngày X" pattern (without explicit "vào", "cho", etc.)
        day_patterns = [
            r"ngày\s+(\d+)",  # "ngày 4", "ngày 1"
            r"day\s+(\d+)",   # "day 4", "day 1"
            r"ngày\s+(\d+)\s*[,và]",  # "ngày 4,", "ngày 1 và"
            r"vào\s+ngày\s+(\d+)",    # "vào ngày 4"
            r"cho\s+ngày\s+(\d+)",    # "cho ngày 4"
            r"với\s+ngày\s+(\d+)",    # "với ngày 4"
            r"ở\s+ngày\s+(\d+)",      # "ở ngày 4"
            r"ngày\s+(\d+)\s+thêm",   # "ngày 4 thêm"
        ]
        has_day_spec = any(re.search(pattern, message_lower) for pattern in day_patterns)
        
        # Also check if message contains just "ngày X" with food keywords nearby
        # This handles cases like "thêm quán ăn ngày 4" or "ngày 4 thêm nhà hàng"
        if not has_day_spec and has_food_keyword:
            # Try to find day number anywhere in message
            day_match = re.search(r"(\d+)", message_lower)
            if day_match:
                # Check if the number is likely a day (between 1-31, and context suggests it's a day)
                day_num = int(day_match.group(1))
                if 1 <= day_num <= 31:
                    # Check if food keyword and day number are close together (within 20 chars)
                    food_positions = [message_lower.find(kw) for kw in food_keywords if kw in message_lower]
                    day_pos = day_match.start()
                    if any(abs(fp - day_pos) < 20 for fp in food_positions if fp != -1):
                        has_day_spec = True
        
        return has_food_keyword and has_day_spec

    # -----------------------------
    # 8.5. Detect partial modification (add activity to specific day)
    # -----------------------------
    def detect_partial_modification(self, message: str) -> bool:
        """
        Detect if user wants to modify/add activity to a specific day in existing itinerary.
        This includes adding activities like karaoke, bars, attractions to specific days.
        Examples: "thêm karaoke vào đêm ngày 2", "thêm bar vào ngày 3", "thêm hoạt động vào ngày 1"
        
        Returns True if this is a partial modification request (should skip confirmation).
        """
        import re
        message_lower = message.lower()
        
        # Check for modification keywords
        modification_keywords = [
            "thêm", "add", "cho thêm", "muốn thêm", "cần thêm",
            "sửa", "đổi", "thay đổi", "chỉnh sửa"
        ]
        has_modification_keyword = any(keyword in message_lower for keyword in modification_keywords)
        
        # Check for day specification patterns (including "đêm ngày X", "tối ngày X", "sau khi ăn tối")
        day_patterns = [
            r"ngày\s+(\d+)",           # "ngày 2", "ngày 3"
            r"day\s+(\d+)",            # "day 2", "day 3"
            r"vào\s+ngày\s+(\d+)",     # "vào ngày 2"
            r"cho\s+ngày\s+(\d+)",     # "cho ngày 2"
            r"đêm\s+ngày\s+(\d+)",     # "đêm ngày 2"
            r"tối\s+ngày\s+(\d+)",     # "tối ngày 2"
            r"sau\s+khi\s+ăn\s+tối",    # "sau khi ăn tối" (implies specific day context)
            r"vào\s+đêm\s+ngày\s+(\d+)", # "vào đêm ngày 2"
        ]
        has_day_spec = any(re.search(pattern, message_lower) for pattern in day_patterns)
        
        # Check for activity keywords (not just food)
        activity_keywords = [
            "karaoke", "bar", "pub", "club", "hoạt động", "activity", "activities",
            "điểm tham quan", "attraction", "địa điểm", "place", "quán", "cà phê",
            "coffee", "cafe", "nhà hàng", "restaurant", "quán ăn", "food"
        ]
        has_activity_keyword = any(keyword in message_lower for keyword in activity_keywords)
        
        # Partial modification: has modification keyword + (day spec OR activity keyword)
        # This catches cases like:
        # - "thêm karaoke vào đêm ngày 2" (modification + activity + day)
        # - "thêm bar vào ngày 3" (modification + activity + day)
        # - "thêm hoạt động vào ngày 1" (modification + activity + day)
        # - "thêm quán ăn vào ngày 2" (modification + activity + day)
        # - "thêm karaoke vào đêm ngày 2 sau khi ăn tối" (modification + activity + day context)
        is_partial = has_modification_keyword and (has_day_spec or has_activity_keyword)
        
        # Exclude full plan changes (city, duration, budget changes)
        # If message mentions city change or duration change, it's NOT partial modification
        # Check if it's a duration change (e.g., "sửa thành 4 ngày", "thay đổi thành 5 ngày")
        duration_change_patterns = [
            r"sửa\s+thành\s+(\d+)\s+ngày",
            r"thay\s+đổi\s+thành\s+(\d+)\s+ngày",
            r"đổi\s+thành\s+(\d+)\s+ngày",
            r"(\d+)\s+ngày\s+(\d+)\s+đêm",  # "5 ngày 4 đêm" (full duration change)
            r"lịch\s+(\d+)\s+ngày",         # "lịch 4 ngày"
        ]
        is_duration_change = any(re.search(pattern, message_lower) for pattern in duration_change_patterns)
        
        # If it's a duration change, it's NOT a partial modification
        if is_duration_change:
            return False
        
        # Also exclude city changes
        city_change_keywords = ["thành phố", "city", "địa điểm mới", "đổi thành phố"]
        has_city_change = any(keyword in message_lower for keyword in city_change_keywords)
        
        # Check if it's replacing a specific place (e.g., "đổi địa điểm X thành Y")
        # Pattern: "đổi [place name] thành" or "thay thế [place name] thành"
        replace_patterns = [
            r"đổi\s+địa\s+điểm\s+.+?\s+thành",
            r"thay\s+thế\s+.+?\s+thành",
            r"đổi\s+.+?\s+thành\s+địa\s+điểm",
            r"thay\s+.+?\s+bằng",
        ]
        is_replace_activity = any(re.search(pattern, message_lower) for pattern in replace_patterns)
        
        # If it's replacing a specific activity/place, it's a partial modification
        if is_replace_activity:
            logger.info(f"Detected replace activity request: {message_lower}")
            return True
        
        if has_city_change and not has_day_spec and not is_replace_activity:
            # If mentions city change but no specific day and not replacing activity, it's a full change
            return False
        
        return is_partial

    # -----------------------------
    # 9. Parse day index from message
    # -----------------------------
    def parse_day_from_message(self, message: str) -> Optional[int]:
        """
        Parse day number from message.
        Example: "ngày 4" -> dayIndex = 3 (0-based)
        Handles various patterns: "ngày 4", "day 4", "vào ngày 4", "cho ngày 4", etc.
        """
        message_lower = message.lower()
        
        # Try to find day number (expanded patterns, ordered by specificity)
        day_patterns = [
            r"vào\s+ngày\s+(\d+)",      # "vào ngày 4"
            r"cho\s+ngày\s+(\d+)",      # "cho ngày 4"
            r"với\s+ngày\s+(\d+)",      # "với ngày 4"
            r"ở\s+ngày\s+(\d+)",        # "ở ngày 4"
            r"ngày\s+(\d+)\s+thêm",     # "ngày 4 thêm"
            r"ngày\s+(\d+)\s*[,và]",    # "ngày 4,", "ngày 4 và"
            r"ngày\s+(\d+)",            # "ngày 4" (most common)
            r"day\s+(\d+)",             # "day 4"
        ]
        
        for pattern in day_patterns:
            match = re.search(pattern, message_lower)
            if match:
                day_num = int(match.group(1))
                # Convert to 0-based index
                day_index = day_num - 1
                if day_index >= 0:
                    logger.info(f"Parsed day number {day_num} from message (0-based index: {day_index})")
                    return day_index
        
        # Fallback: Try to find any number that could be a day (1-31)
        # This handles cases like "thêm quán ăn 4" where "4" might refer to day 4
        fallback_match = re.search(r"\b(\d+)\b", message_lower)
        if fallback_match:
            day_num = int(fallback_match.group(1))
            if 1 <= day_num <= 31:
                day_index = day_num - 1
                logger.info(f"Fallback: Parsed day number {day_num} from message (0-based index: {day_index})")
                return day_index
        
        return None

    # -----------------------------
    # 10. Add food to specific day
    # -----------------------------
    async def add_food_to_day(
        self,
        itinerary: dict,
        day_index: int,
        city: str,
        min_count: int = 2
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Add new restaurants to a specific day, ensuring no duplicates across entire trip.
        Only adds 2-3 NEW restaurants, does NOT remove or replace existing activities.
        
        Args:
            itinerary: Current itinerary dict
            day_index: Target day index (0-based)
            city: City name for search
            min_count: Minimum number of restaurants to add (default: 2, max: 3)
        
        Returns:
            tuple: (list of added restaurants, formatted response message)
        """
        from app.services.place_service import PlaceService
        
        place_service = PlaceService()
        
        # 1. Collect ALL restaurants from entire itinerary
        # Check both segments (category="food") and foods field if exists
        used_restaurants = []
        days = itinerary.get("days", [])
        
        for day in days:
            # Collect from segments (main storage)
            segments = day.get("segments", [])
            for segment in segments:
                # Only collect food/restaurant segments
                if segment.get("category") == "food":
                    name = segment.get("name", "").strip()
                    if name:
                        used_restaurants.append(name)
            
            # Also check foods field if exists (for compatibility)
            foods = day.get("foods", [])
            if isinstance(foods, list):
                for food in foods:
                    if isinstance(food, dict):
                        name = food.get("name", "").strip()
                    elif isinstance(food, str):
                        name = food.strip()
                    else:
                        name = str(food).strip()
                    if name:
                        used_restaurants.append(name)
        
        # Normalize all used restaurant names for duplicate checking
        def normalize_name(name: str) -> str:
            """Normalize: lowercase + remove accents + trim punctuation"""
            if not name:
                return ""
            # Use place_service normalization
            normalized = place_service._normalize_vietnamese_text(name)
            # Remove punctuation
            normalized = re.sub(r'[^\w\s]', '', normalized)
            return normalized.strip()
        
        used_normalized = {normalize_name(name) for name in used_restaurants}
        logger.info(f"Found {len(used_restaurants)} restaurants already in itinerary (normalized: {len(used_normalized)} unique)")
        
        # 2. Query Google Places with expanded search
        # Use multiple queries to get variety
        queries = [
            f"quán ăn tại {city}",
            f"nhà hàng ngon tại {city}",
            f"món địa phương tại {city}",
            f"street food tại {city}",
            f"restaurant tại {city}",
            f"quán ăn địa phương tại {city}",
            f"nhà hàng buffet tại {city}",
            f"quán lẩu tại {city}",
            f"nhà hàng BBQ tại {city}",
            f"nhà hàng hải sản tại {city}",
        ]
        
        # City-specific local cuisine keywords
        city_lower = city.lower()
        local_keywords = []
        if "hà nội" in city_lower or "hanoi" in city_lower:
            local_keywords = ["phở", "bún chả", "bún bò", "chả cá", "bún đậu"]
        elif "hồ chí minh" in city_lower or "hcm" in city_lower or "saigon" in city_lower:
            local_keywords = ["cơm tấm", "bánh mì", "hủ tiếu", "bún riêu", "bánh xèo"]
        else:
            local_keywords = ["phở", "bún", "lẩu", "hải sản"]
        
        # Add local cuisine queries
        for keyword in local_keywords[:5]:
            queries.append(f"{keyword} tại {city}")
        
        # Fetch places with multiple queries
        # Avoid chain restaurants - only 1 per chain
        all_places = []
        seen_places = set()
        seen_chains = set()
        
        for query in queries:
            places = place_service.maps.search_places(query, limit=20)
            for place in places:
                name = place.get("displayName", {}).get("text", "").strip()
                if not name:
                    continue
                
                normalized_name = normalize_name(name)
                if normalized_name in seen_places:
                    continue
                
                # Check if it's a chain restaurant
                chain_name = place_service._extract_chain_name(name)
                if chain_name in place_service.chain_restaurants:
                    if chain_name in seen_chains:
                        continue  # Skip duplicate chain
                    seen_chains.add(chain_name)
                
                seen_places.add(normalized_name)
                all_places.append(place)
        
        # 3. Normalize and filter with strict quality filters
        # Filter: rating >= 4.2, reviewCount >= 500 (for better quality)
        # Note: place_service._normalize_places also filters rating >= 4.2, but we do it here too for clarity
        filtered_places = []
        for place in all_places:
            rating = place.get("rating", 0)
            votes = place.get("userRatingCount", 0)
            
            # Strict quality filters: rating >= 4.2, reviewCount >= 500
            if rating < 4.2:
                continue
            if votes < 500:
                continue
            
            # Check if already used (normalized comparison)
            name = place.get("displayName", {}).get("text", "").strip()
            normalized_name = normalize_name(name)
            if normalized_name in used_normalized:
                continue
            
            filtered_places.append(place)
        
        # Normalize places using place_service
        # place_service._normalize_places will apply additional filters (rating >= 4.2, has photos, etc.)
        normalized_places = place_service._normalize_places(
            filtered_places,
            force_category="food",
            city=city
        )
        
        # Filter again after normalization to ensure no duplicates slipped through
        final_normalized = []
        final_seen = set()
        for place in normalized_places:
            place_name = normalize_name(place.get("name", ""))
            if place_name not in final_seen and place_name not in used_normalized:
                final_seen.add(place_name)
                final_normalized.append(place)
        
        normalized_places = final_normalized
        
        # Sort by rating desc, then review count desc
        normalized_places.sort(key=lambda x: (
            -x.get("rating", 0),
            -x.get("votes", 0)
        ))
        
        # Only take 2-3 restaurants (not all available ones)
        # Prefer 2-3 restaurants, but accept 2 if that's all we have
        # Limit to max 3 restaurants, minimum 2
        if len(normalized_places) >= 3:
            # If we have 3+ options, take 3 (prefer more variety)
            actual_count = 3
        elif len(normalized_places) >= 2:
            # If we have 2 options, take 2
            actual_count = 2
        else:
            # If we have less than 2, take what we have (but log warning)
            actual_count = len(normalized_places)
        
        new_restaurants = normalized_places[:actual_count]
        
        if len(new_restaurants) < min_count:
            logger.warning(f"Only found {len(new_restaurants)} new restaurants (wanted: {min_count})")
        else:
            logger.info(f"Adding {len(new_restaurants)} new restaurants to day {day_index + 1} (limited to 2-3, keeping all previous restaurants)")
        
        # 4. Add to target day (APPEND ONLY - do NOT remove or replace existing activities)
        if day_index < len(days):
            target_day = days[day_index]
            segments = target_day.get("segments", [])
            
            # Count existing activities before adding
            existing_count = len(segments)
            existing_food_count = sum(1 for seg in segments if seg.get("category") == "food")
            
            # Add restaurants as food segments (APPEND ONLY)
            for restaurant in new_restaurants:
                segments.append({
                    "type": "activity",
                    "name": restaurant.get("name", ""),
                    "address": restaurant.get("address", ""),
                    "duration_min": restaurant.get("duration_min", 75),
                    "estimated_cost_vnd": restaurant.get("estimated_cost_vnd", 0),
                    "category": "food",
                    "rating": restaurant.get("rating"),
                    "votes": restaurant.get("votes", 0),
                    "price_level": restaurant.get("price_level"),
                    "coordinates": restaurant.get("coordinates"),
                    "description": restaurant.get("description", ""),
                })
            
            target_day["segments"] = segments
            
            # Log confirmation that we only appended, didn't remove anything
            new_count = len(segments)
            new_food_count = sum(1 for seg in segments if seg.get("category") == "food")
            logger.info(
                f"Added {len(new_restaurants)} NEW restaurants to day {day_index + 1}. "
                f"Existing activities: {existing_count} (food: {existing_food_count}), "
                f"Total after adding: {new_count} (food: {new_food_count}). "
                f"All existing activities preserved."
            )
        
        # 5. Format response
        response_message = self._format_added_food_response(new_restaurants, day_index + 1)
        
        return new_restaurants, response_message

    # -----------------------------
    # 11. Format added food response
    # -----------------------------
    def _format_added_food_response(self, restaurants: list, day_number: int) -> str:
        """
        Format response showing only the added restaurants.
        Format:
        📌 Đã thêm quán ăn mới cho Ngày X:
        
        🍽 <b>Restaurant Name</b>
        ⭐ 4.5/5 · 3,200 đánh giá
        💵 ₫₫ | 🍽️ Món nổi bật: <signature dish>
        📍 <Short address>
        Mô tả: <1–2 sentence clear description>
        """
        if not restaurants:
            return f"Xin lỗi, không tìm thấy quán ăn mới nào cho Ngày {day_number}."
        
        response = f"📌 Đã thêm quán ăn mới cho Ngày {day_number}:\n\n"
        
        for restaurant in restaurants:
            name = restaurant.get("name", "")
            rating = restaurant.get("rating", 0)
            votes = restaurant.get("votes", 0) or restaurant.get("userRatingCount", 0)
            price_level = restaurant.get("price_level")
            estimated_cost_vnd = restaurant.get("estimated_cost_vnd", 0)
            address = restaurant.get("address", "")
            description = restaurant.get("description", "")
            
            # Format rating
            rating_str = f"{rating:.1f}" if rating else "0"
            votes_str = f"{votes:,}".replace(",", ".") if votes else "0"
            
            # Format price range
            price_range = ""
            if price_level is not None:
                price_symbols = {0: "₫", 1: "₫₫", 2: "₫₫₫", 3: "₫₫₫₫", 4: "₫₫₫₫"}
                price_range = price_symbols.get(price_level, "₫")
            elif estimated_cost_vnd > 0:
                per_person = estimated_cost_vnd // 2
                if per_person < 100000:
                    price_range = f"{per_person:,.0f}đ/người".replace(",", ".")
                else:
                    price_range = f"{per_person//1000:.0f}kđ/người"
            
            # Extract signature dish from description or infer from name
            signature_dish = ""
            name_lower = name.lower()
            if "phở" in name_lower:
                if "bò" in name_lower:
                    signature_dish = "Phở bò tái chín, nước dùng trong và ngọt xương"
                elif "gà" in name_lower:
                    signature_dish = "Phở gà thơm ngon, nước dùng đậm đà"
                else:
                    signature_dish = "Phở bò truyền thống, nước dùng trong và ngọt xương"
            elif "bún chả" in name_lower:
                signature_dish = "Bún chả truyền thống, thịt nướng thơm lừng"
            elif "bún bò" in name_lower:
                signature_dish = "Bún bò Huế, nước dùng cay nồng"
            elif "chả cá" in name_lower:
                signature_dish = "Chả cá Lã Vọng, cá nướng thơm và nghệ tươi"
            elif "lẩu" in name_lower:
                signature_dish = "Lẩu nóng hổi, nước dùng đậm đà"
            elif "bbq" in name_lower or "nướng" in name_lower:
                signature_dish = "Đồ nướng tươi ngon, thịt mềm và đậm vị"
            elif "hải sản" in name_lower or "seafood" in name_lower:
                signature_dish = "Hải sản tươi sống, chế biến đa dạng"
            elif "bánh mì" in name_lower:
                signature_dish = "Bánh mì giòn tan, nhân đầy đặn"
            elif "cơm tấm" in name_lower:
                signature_dish = "Cơm tấm Sài Gòn, sườn nướng thơm"
            elif "bánh xèo" in name_lower:
                signature_dish = "Bánh xèo giòn rụm, nhân tôm thịt đầy đặn"
            else:
                # Try to extract from description
                if description:
                    if "phở" in description.lower():
                        signature_dish = "Phở truyền thống"
                    elif "bún" in description.lower():
                        signature_dish = "Bún đặc biệt"
                    else:
                        signature_dish = "Món địa phương đặc trưng"
                else:
                    signature_dish = "Món địa phương đặc trưng"
            
            # Build formatted entry
            response += f"🍽 <b>{name}</b>\n"
            response += f"⭐ {rating_str}/5 · {votes_str} đánh giá\n"
            
            if price_range:
                response += f"💵 {price_range} | 🍽️ Món nổi bật: {signature_dish}\n"
            else:
                response += f"🍽️ Món nổi bật: {signature_dish}\n"
            
            if address:
                # Shorten address if too long
                short_address = address
                if len(address) > 60:
                    parts = address.split(",")
                    if len(parts) >= 2:
                        short_address = ",".join(parts[:2]).strip()
                response += f"📍 {short_address}\n"
            
            # Use description if available, otherwise create simple one
            if description:
                # Ensure description is max 2 sentences
                sentences = description.split(".")
                if len(sentences) > 2:
                    description = ". ".join(sentences[:2]).strip()
                    if not description.endswith("."):
                        description += "."
                response += f"Mô tả: {description}\n"
            else:
                response += f"Mô tả: Quán ăn nổi tiếng, được đánh giá cao bởi khách hàng.\n"
            
            response += "\n"
        
        return response.strip()
