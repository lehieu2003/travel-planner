# backend/app/api/routes_plan.py

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from datetime import datetime, timedelta
import json
import re

from app.agents.planner_orchestrator import PlannerOrchestrator
from app.agents.llm_agent import LLMAgent
from app.db.sqlite_memory import SQLiteMemory
from app.core.security import decode_token
from app.core.logger import logger
from app.services.google_maps_service import GoogleMapsService

router = APIRouter(prefix="/plan", tags=["planner"])

db = SQLiteMemory()
planner = PlannerOrchestrator()
llm_agent = LLMAgent()
maps_service = GoogleMapsService()


# --------------------------
# Request model
# --------------------------
class PlanRequest(BaseModel):
    conversation_id: str
    hard_constraints: dict
    soft_constraints: Optional[dict] = {}
    user_prompt: Optional[str] = ""


class MessagePlanRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# --------------------------
# Extract user ID
# --------------------------
def get_user_id(authorization: Optional[str]) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")
    payload = decode_token(authorization.split(" ")[1])
    if not payload:
        raise HTTPException(401, "Invalid token")
    return int(payload["sub"])


# --------------------------
# Transform itinerary from backend format to frontend format
# --------------------------
def _transform_itinerary_for_frontend(itinerary: dict, city: str, duration_days: int, budget_vnd: int) -> dict:
    """
    Transform itinerary from planner format to frontend expected format.
    """
    logger.info(f"Transforming itinerary: {len(itinerary.get('days', []))} days")
    
    # Format budget
    budget_str = f"{budget_vnd:,}".replace(",", ".")
    
    # Format duration
    nights = max(0, duration_days - 1)
    if nights > 0:
        duration_str = f"{duration_days} ngày {nights} đêm"
    else:
        duration_str = f"{duration_days} ngày"
    
    # Transform days
    transformed_days = []
    for idx, day_data in enumerate(itinerary.get("days", []), 1):
        segments = day_data.get("segments", [])
        logger.info(f"Day {idx}: {len(segments)} segments found")
        
        # Separate meals and non-meal activities
        meals = []  # Activities with meal_type
        non_meals = []  # Other activities
        
        for segment in segments:
            if segment.get("type") == "activity":
                meal_type = segment.get("meal_type")
                if meal_type in ["breakfast", "lunch", "dinner"]:
                    meals.append((segment, meal_type))
                else:
                    non_meals.append(segment)
        
        # Define meal times (in minutes from midnight)
        # Meal time windows: Breakfast 07:00-09:00, Lunch 11:30-13:30, Dinner 18:00-20:00
        meal_times = {
            "breakfast": 8 * 60,      # 8:00 AM (middle of 07:00-09:00 window)
            "lunch": 12 * 60 + 30,    # 12:30 PM (middle of 11:30-13:30 window)
            "dinner": 19 * 60          # 7:00 PM (middle of 18:00-20:00 window)
        }
        
        # Create a list of all activities with their scheduled times
        scheduled_activities = []
        
        # Schedule meals at fixed times
        for segment, meal_type in meals:
            meal_time_minutes = meal_times.get(meal_type, 8 * 60)
            meal_hour = meal_time_minutes // 60
            meal_min = meal_time_minutes % 60
            scheduled_activities.append({
                "segment": segment,
                "time_minutes": meal_time_minutes,
                "time_str": f"{meal_hour:02d}:{meal_min:02d}",
                "is_meal": True
            })
        
        # Schedule non-meal activities around meals
        # Define time slots: before breakfast, after breakfast-before lunch, after lunch-before dinner, after dinner
        time_slots = [
            (7 * 60, meal_times["breakfast"] - 30),  # Before breakfast: 7:00 - 7:30
            (meal_times["breakfast"] + 90, meal_times["lunch"] - 30),  # After breakfast: 9:30 - 11:30
            (meal_times["lunch"] + 90, meal_times["dinner"] - 30),  # After lunch: 13:30 - 18:30
            (meal_times["dinner"] + 90, 22 * 60),  # After dinner: 20:30 - 22:00
        ]
        
        current_slot_idx = 0
        current_time_minutes = time_slots[0][0] if time_slots else 7 * 60
        
        for segment in non_meals:
            duration_min = segment.get("duration_min", 60)
            travel_time_min = segment.get("travel_time_min", 0) or 0
            total_duration = duration_min + travel_time_min + 30  # Include buffer
            
            # Find a suitable time slot for this activity
            scheduled = False
            attempts = 0
            max_attempts = len(time_slots) * 2  # Try all slots
            
            while not scheduled and attempts < max_attempts:
                slot_start, slot_end = time_slots[current_slot_idx]
                
                # Check if activity fits in current slot
                if current_time_minutes + total_duration <= slot_end:
                    # Activity fits, schedule it
                    hour = current_time_minutes // 60
                    minute = current_time_minutes % 60
                    scheduled_activities.append({
                        "segment": segment,
                        "time_minutes": current_time_minutes,
                        "time_str": f"{hour:02d}:{minute:02d}",
                        "is_meal": False
                    })
                    
                    # Move to next time slot
                    current_time_minutes += total_duration
                    scheduled = True
                else:
                    # Activity doesn't fit, try next slot
                    current_slot_idx = (current_slot_idx + 1) % len(time_slots)
                    if current_slot_idx == 0:
                        # Reset to start of first slot if we've cycled through all
                        current_time_minutes = time_slots[0][0]
                    else:
                        current_time_minutes = time_slots[current_slot_idx][0]
                    attempts += 1
            
            # If we couldn't schedule it, put it at the end of the last slot
            if not scheduled:
                last_slot_end = time_slots[-1][1]
                hour = last_slot_end // 60
                minute = last_slot_end % 60
                scheduled_activities.append({
                    "segment": segment,
                    "time_minutes": last_slot_end,
                    "time_str": f"{hour:02d}:{minute:02d}",
                    "is_meal": False
                })
        
        # Create a mapping of (current_segment_name, next_segment_name) -> travel_time_info
        # This allows us to look up travel time after sorting by segment names
        travel_time_map = {}
        for i in range(len(segments) - 1):
            current_seg = segments[i]
            next_seg = segments[i + 1]
            
            # Only map if both are activities
            if (current_seg.get("type") == "activity" and 
                next_seg.get("type") == "activity"):
                current_name = current_seg.get("name", "")
                next_name = next_seg.get("name", "")
                
                # Only add to map if travel time was actually calculated (not None and > 0)
                travel_time_to_next = current_seg.get("travelTimeToNext")
                if current_name and next_name and travel_time_to_next is not None and travel_time_to_next > 0:
                    travel_time_map[(current_name, next_name)] = {
                        "travelTimeToNext": travel_time_to_next,
                        "distanceToNext": current_seg.get("distanceToNext")
                    }
        
        # Sort all activities by time
        scheduled_activities.sort(key=lambda x: x["time_minutes"])
        
        # Build activities list
        activities = []
        for act_idx, scheduled in enumerate(scheduled_activities):
            segment = scheduled["segment"]
            time_str = scheduled["time_str"]
            
            # Get duration and travel time
            duration_min = segment.get("duration_min", 60)
            travel_time_min = segment.get("travel_time_min", 0) or 0
            
            # Format activity duration string
            if duration_min >= 60:
                hours = duration_min // 60
                mins = duration_min % 60
                if mins > 0:
                    activity_duration_str = f"{hours} giờ {mins} phút"
                else:
                    activity_duration_str = f"{hours} giờ"
            else:
                activity_duration_str = f"{duration_min} phút"
            
            # Format cost
            cost_vnd = segment.get("estimated_cost_vnd", 0)
            cost_str = None
            if cost_vnd and cost_vnd > 0:
                if cost_vnd >= 1000000:
                    cost_str = f"{cost_vnd / 1000000:.1f} triệu VNĐ"
                elif cost_vnd >= 1000:
                    cost_str = f"{cost_vnd / 1000:.0f}k VNĐ"
                else:
                    cost_str = f"{cost_vnd:,} VNĐ".replace(",", ".")
            
            # Format travel time
            travel_time_min = segment.get("travel_time_min", 0) or 0
            travel_time_str = None
            if travel_time_min > 0:
                if travel_time_min >= 60:
                    hours = travel_time_min // 60
                    mins = travel_time_min % 60
                    if mins > 0:
                        travel_time_str = f"{hours}h{mins}m"
                    else:
                        travel_time_str = f"{hours}h"
                else:
                    travel_time_str = f"{travel_time_min} phút"
            
            # Get travel time to next activity based on sorted order
            # Look up travel time from current segment to next segment in sorted list
            travel_time_to_next_min = None
            distance_to_next_m = None
            
            if act_idx < len(scheduled_activities) - 1:
                next_scheduled = scheduled_activities[act_idx + 1]
                next_segment = next_scheduled["segment"]
                
                current_segment_name = segment.get("name", "")
                next_segment_name = next_segment.get("name", "")
                
                # Look up travel time from mapping
                if current_segment_name and next_segment_name:
                    travel_info = travel_time_map.get((current_segment_name, next_segment_name))
                    if travel_info:
                        travel_time_to_next_min = travel_info.get("travelTimeToNext")
                        distance_to_next_m = travel_info.get("distanceToNext")
            
            # Format travel time to next
            travel_time_to_next_str = None
            if travel_time_to_next_min and travel_time_to_next_min > 0:
                if travel_time_to_next_min >= 60:
                    hours = travel_time_to_next_min // 60
                    mins = travel_time_to_next_min % 60
                    if mins > 0:
                        travel_time_to_next_str = f"{hours} giờ {mins} phút"
                    else:
                        travel_time_to_next_str = f"{hours} giờ"
                else:
                    travel_time_to_next_str = f"{travel_time_to_next_min} phút"
            
            activities.append({
                "id": f"act-{idx}-{act_idx}",
                "name": segment.get("name", ""),
                "icon": segment.get("category", "culture") or "culture",
                "time": time_str,
                "duration": activity_duration_str,
                "rating": segment.get("rating"),
                "address": segment.get("address"),
                "cost": cost_str,
                "travelTime": travel_time_str,
                "travelTimeToNext": travel_time_to_next_str,  # Formatted string for display
                "travelTimeToNextMinutes": travel_time_to_next_min,  # Raw minutes for calculations
                "distanceToNext": distance_to_next_m  # Distance in meters
            })
        
        logger.info(f"Day {idx}: {len(activities)} activities transformed")
        transformed_days.append({
            "day": idx,
            "date": day_data.get("date", ""),
            "activities": activities
        })
    
    # Transform hotel
    hotel_info = None
    hotel_data = itinerary.get("hotel")
    if hotel_data:
        price_str = str(hotel_data.get("price", ""))
        if price_str and not price_str.endswith("VNĐ"):
            # Try to format price
            try:
                price_num = float(price_str.replace(".", "").replace(",", ""))
                price_str = f"{price_num:,.0f}".replace(",", ".")
            except:
                pass
        
        hotel_info = {
            "name": hotel_data.get("name", ""),
            "price": price_str or "Liên hệ",
            "rating": hotel_data.get("rating"),
            "image": hotel_data.get("image") or hotel_data.get("photo")
        }
    
    return {
        "destination": city,
        "duration": duration_str,
        "budget": f"{budget_str} VNĐ",
        "days": transformed_days,
        "hotel": hotel_info
    }


# --------------------------
# NEW ENDPOINT: Handle natural language message (main endpoint for frontend)
# --------------------------
@router.post("/", tags=["planner"])
async def plan_from_message(data: MessagePlanRequest, authorization: Optional[str] = Header(None)):
    """
    Endpoint mới để xử lý message tự nhiên từ frontend.
    Tự động extract constraints và tạo plan hoặc chat với user.
    """
    user_id = get_user_id(authorization)
    
    # Load conversation history if conversation_id provided
    conversation_history = []
    conversation_id = data.conversation_id
    
    if conversation_id:
        conv = db.get_conversation(conversation_id)
        if not conv or str(conv["user_id"]) != str(user_id):
            raise HTTPException(403, "Access denied to this conversation")
        messages = db.get_messages(conversation_id)
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
    else:
        # Create new conversation
        conversation_id = str(uuid4())
        title = data.message[:30] + ("..." if len(data.message) > 30 else "")
        db.create_conversation(conversation_id, str(user_id), title)
    
    # Save user message to database
    user_message_id = str(uuid4())
    db.add_message(user_message_id, conversation_id, "user", data.message)
    
    # Add current message to conversation_history for context
    # This ensures the current message is included when processing modification requests
    conversation_history.append({
        "role": "user",
        "content": data.message
    })
    
    # ALWAYS try to get previous itinerary from conversation history if conversation_id exists
    # This allows us to use historical context even if modification is not explicitly detected
    previous_itinerary = None
    if conversation_id:
        previous_itinerary = db.get_last_itinerary(conversation_id)
        if previous_itinerary:
            logger.info(f"Previous itinerary found in conversation history: {len(previous_itinerary.get('days', []))} days, destination: {previous_itinerary.get('destination', 'N/A')}")
        else:
            logger.info(f"No previous itinerary found in conversation {conversation_id}")
    
    # Get user configs from database (energy_level, budget_min, budget_max, preference_json)
    user_profile = db.get_user_by_id(user_id)
    user_configs = None
    if user_profile:
        user_configs = {
            "energy_level": user_profile.get("energy_level"),
            "budget_min": user_profile.get("budget_min"),
            "budget_max": user_profile.get("budget_max"),
            "preferences_json": user_profile.get("preferences_json")
        }
        logger.info(f"Loaded user configs: energy_level={user_configs['energy_level']}, budget_min={user_configs['budget_min']}, budget_max={user_configs['budget_max']}, preferences_json={user_configs['preferences_json']}")
    
    # Extract plan data from message (now includes current message in history)
    # Pass previous_itinerary info and user_configs to help LLM understand context better
    extracted_data = await llm_agent.extract_plan_data(data.message, conversation_history, user_configs)
    logger.info(f"Extracted data from message '{data.message}': {extracted_data}")
    
    # Check request type
    request_type = extracted_data.get("request_type")
    is_modification = extracted_data.get("is_modification", False)
    
    # Auto-detect modification if we have previous itinerary and user message suggests modification
    # This helps catch cases where LLM didn't explicitly mark as modification
    if previous_itinerary and not is_modification:
        # Check if message suggests modification (e.g., "sửa", "thay đổi", "đổi", numbers without city)
        modification_keywords = ["sửa", "thay đổi", "đổi", "chỉnh", "muốn", "cần"]
        message_lower = data.message.lower()
        has_modification_keyword = any(keyword in message_lower for keyword in modification_keywords)
        has_number_without_city = (
            any(char.isdigit() for char in data.message) and 
            not extracted_data.get("city") and
            (extracted_data.get("duration_days") or extracted_data.get("budget_vnd"))
        )
        
        if has_modification_keyword or has_number_without_city:
            is_modification = True
            logger.info(f"Auto-detected modification request based on previous itinerary and message context")
    
    # Extract city early (needed for list requests)
    city = extracted_data.get("city")
    if not city and previous_itinerary:
        city = previous_itinerary.get("destination")
    
    # Handle Add Food Mode - check BEFORE other requests
    # This mode adds restaurants to a specific day without regenerating the entire trip
    if previous_itinerary and llm_agent.detect_add_food_mode(data.message):
        logger.info("Add Food Mode detected - adding restaurants to specific day")
        
        # Parse day index from message
        day_index = llm_agent.parse_day_from_message(data.message)
        if day_index is None:
            # If day not specified, ask user
            clarification_message = "Bạn muốn thêm quán ăn cho ngày nào? Vui lòng chỉ rõ ngày (ví dụ: ngày 1, ngày 2, ...)"
            assistant_message_id = str(uuid4())
            db.add_message(assistant_message_id, conversation_id, "assistant", clarification_message)
            return {
                "ok": True,
                "requires_clarification": True,
                "clarification_message": clarification_message,
                "conversation_id": conversation_id
            }
        
        # Check if day_index is valid
        days = previous_itinerary.get("days", [])
        if day_index >= len(days):
            error_message = f"Ngày {day_index + 1} không tồn tại trong lịch trình. Lịch trình hiện có {len(days)} ngày."
            assistant_message_id = str(uuid4())
            db.add_message(assistant_message_id, conversation_id, "assistant", error_message)
            return {
                "ok": True,
                "error": True,
                "error_message": error_message,
                "conversation_id": conversation_id
            }
        
        # Get city from previous itinerary if not in message
        if not city:
            city = previous_itinerary.get("destination")
        
        if not city:
            error_message = "Không tìm thấy thông tin thành phố trong lịch trình. Vui lòng thử lại."
            assistant_message_id = str(uuid4())
            db.add_message(assistant_message_id, conversation_id, "assistant", error_message)
            return {
                "ok": True,
                "error": True,
                "error_message": error_message,
                "conversation_id": conversation_id
            }
        
        try:
            # Add restaurants to the specific day
            # Only add 2-3 new restaurants, do NOT remove existing activities
            added_restaurants, response_message = await llm_agent.add_food_to_day(
                previous_itinerary,
                day_index,
                city,
                min_count=2  # Minimum 2, maximum 3 restaurants
            )
            
            # Transform itinerary for frontend (to return updated itinerary)
            # Get budget from previous itinerary
            budget_alloc = previous_itinerary.get("budget_allocation", {})
            total_budget = (
                budget_alloc.get("hotel", 0) +
                budget_alloc.get("activities", 0) +
                budget_alloc.get("food", 0) +
                budget_alloc.get("transport", 0)
            ) if budget_alloc else 0
            
            transformed_itinerary = _transform_itinerary_for_frontend(
                previous_itinerary,
                city,
                len(days),
                total_budget
            )
            
            # Save assistant message with updated itinerary
            assistant_message_id = str(uuid4())
            db.add_message(
                assistant_message_id,
                conversation_id,
                "assistant",
                response_message,
                itinerary_data=transformed_itinerary
            )
            
            return {
                "ok": True,
                "is_add_food": True,
                "added_food_message": response_message,
                "itinerary": transformed_itinerary,  # Return updated itinerary
                "conversation_id": conversation_id
            }
        except Exception as e:
            logger.error(f"Error adding food to day: {e}")
            error_message = f"Xin lỗi, đã có lỗi xảy ra khi thêm quán ăn: {str(e)}"
            assistant_message_id = str(uuid4())
            db.add_message(assistant_message_id, conversation_id, "assistant", error_message)
            return {
                "ok": True,
                "error": True,
                "error_message": error_message,
                "conversation_id": conversation_id
            }
    
    # Handle list requests (restaurant, hotel, activity lists)
    if request_type == "list":
        list_category = extracted_data.get("list_category", "activity")
        
        # Fallback: Check message directly for coffee keywords if LLM missed it
        message_lower = data.message.lower()
        if "cà phê" in message_lower or "ca phe" in message_lower or "coffee" in message_lower or "cafe" in message_lower:
            if "quán cà phê" in message_lower or "quán cafe" in message_lower or "coffee shop" in message_lower:
                list_category = "coffee"
                logger.info(f"Fallback: Detected coffee from message keywords, overriding list_category to 'coffee'")
        
        # Get city from extracted data or previous itinerary
        list_city = city
        if not list_city and previous_itinerary:
            list_city = previous_itinerary.get("destination")
        
        # For restaurant and coffee lists, use formatted list generator
        if list_category in ["restaurant", "coffee"] and list_city:
            try:
                list_message = await llm_agent.generate_formatted_list(
                    list_category=list_category,
                    city=list_city,
                    limit=10
                )
            except Exception as e:
                logger.error(f"Error generating formatted list: {e}")
                # Fallback to chat response
                list_message = await llm_agent.generate_chat_response(
                    f"Người dùng muốn danh sách {list_category} tại {list_city}. Hãy trả lời một cách tự nhiên và hữu ích.",
                    conversation_history
                )
        else:
            # For other list types, use chat response
            list_message = await llm_agent.generate_chat_response(
                f"Người dùng muốn danh sách {list_category}. Hãy trả lời một cách tự nhiên và hữu ích.",
                conversation_history
            )
        
        assistant_message_id = str(uuid4())
        db.add_message(assistant_message_id, conversation_id, "assistant", list_message)
        
        return {
            "ok": True,
            "is_list": True,
            "list_category": list_category,
            "list_message": list_message,
            "conversation_id": conversation_id
        }
    
    # Handle modification requests - now we always have previous_itinerary if it exists
    if is_modification and previous_itinerary:
        logger.info(f"Processing modification request with previous itinerary: {len(previous_itinerary.get('days', []))} days")
        try:
            # Use modify_itinerary to get updated constraints
            # This uses conversation_history to understand full context
            modified_data = await llm_agent.modify_itinerary(
                previous_itinerary,
                data.message,
                extracted_data,
                conversation_history
            )
            # Merge modified_data into extracted_data
            if modified_data:
                extracted_data.update(modified_data)
                logger.info(f"Modified data from conversation history: {modified_data}")
        except Exception as e:
            logger.error(f"Error modifying itinerary: {e}")
            # Continue with original extracted_data if modification fails
    elif is_modification and not previous_itinerary:
        logger.warning(f"Modification request detected but no previous itinerary found. Treating as new request.")
    
    # Extract constraints (city already extracted above for list requests)
    # city = extracted_data.get("city")  # Already extracted above
    budget_vnd = extracted_data.get("budget_vnd")
    duration_days = extracted_data.get("duration_days")
    date_range = extracted_data.get("date_range", {})
    preferences = extracted_data.get("preferences", {})
    
    # If we have previous itinerary, use it to fill missing information
    # This works for both modification requests and follow-up requests in the same conversation
    if previous_itinerary:
        logger.info(f"Using previous itinerary to fill missing information. Previous: city={previous_itinerary.get('destination')}, days={len(previous_itinerary.get('days', []))}")
        
        # Get city from previous itinerary if not provided
        if not city:
            # Try to get from previous itinerary's destination or days
            if previous_itinerary.get("destination"):
                city = previous_itinerary["destination"]
                logger.info(f"Filled missing city from previous itinerary: {city}")
            elif previous_itinerary.get("days") and len(previous_itinerary["days"]) > 0:
                # Try to infer from first day's activities
                first_day = previous_itinerary["days"][0]
                # This is a fallback, ideally destination should be stored
                pass
        
        # Get budget from previous itinerary if not provided
        if not budget_vnd or budget_vnd <= 0:
            budget_alloc = previous_itinerary.get("budget_allocation", {})
            if budget_alloc:
                total_budget = (
                    budget_alloc.get("hotel", 0) +
                    budget_alloc.get("activities", 0) +
                    budget_alloc.get("food", 0) +
                    budget_alloc.get("transport", 0)
                )
                if total_budget > 0:
                    budget_vnd = total_budget
                    logger.info(f"Filled missing budget from previous itinerary: {budget_vnd}")
        
        # Get duration from previous itinerary if not provided
        if not duration_days:
            days = previous_itinerary.get("days", [])
            if days:
                duration_days = len(days)
                logger.info(f"Filled missing duration from previous itinerary: {duration_days} days")
        
        # Get date range from previous itinerary if not provided
        if not date_range.get("start") and previous_itinerary.get("days"):
            days = previous_itinerary["days"]
            if days:
                date_range["start"] = days[0].get("date")
                date_range["end"] = days[-1].get("date")
                logger.info(f"Filled missing date range from previous itinerary: {date_range.get('start')} to {date_range.get('end')}")
        
        # If duration changed, recalculate date_end based on new duration
        if duration_days and date_range.get("start"):
            previous_days_count = len(previous_itinerary.get("days", []))
            if duration_days != previous_days_count:
                # Recalculate date_end based on date_start and new duration
                start_date = datetime.fromisoformat(date_range["start"]).date()
                new_end_date = start_date + timedelta(days=duration_days - 1)
                date_range["end"] = new_end_date.isoformat()
                logger.info(f"Recalculated date_end due to duration change: {date_range.get('start')} to {date_range.get('end')} ({duration_days} days)")
    
    # If budget not provided in prompt, try to get from user profile
    # Note: user_profile is already loaded above, but we'll use it here if needed
    if budget_vnd is None or budget_vnd <= 0:
        if not user_profile:
            user_profile = db.get_user_by_id(user_id)
        if user_profile:
            budget_min = user_profile.get("budget_min")
            budget_max = user_profile.get("budget_max")
            # Use average of min and max if both exist, otherwise use max or min
            if budget_min and budget_max:
                budget_vnd = (budget_min + budget_max) // 2
            elif budget_max:
                budget_vnd = budget_max
            elif budget_min:
                budget_vnd = budget_min
    
    # Get user profile if not already loaded
    if not user_profile:
        user_profile = db.get_user_by_id(user_id)
    
    # Check if we have enough info for planning
    has_city = bool(city)
    has_budget = budget_vnd is not None and budget_vnd > 0
    has_duration = duration_days is not None and duration_days > 0
    has_dates = bool(date_range.get("start") and date_range.get("end"))
    
    # Check if user has budget_min and budget_max in profile (for budget range)
    has_budget_from_profile = False
    if user_profile:
        budget_min = user_profile.get("budget_min")
        budget_max = user_profile.get("budget_max")
        has_budget_from_profile = budget_min is not None and budget_max is not None
    
    # Check if this is a partial modification request (add activity to specific day)
    # Partial modifications should skip confirmation and directly update the itinerary
    is_partial_modification = False
    if previous_itinerary:
        is_partial_modification = llm_agent.detect_partial_modification(data.message)
        if is_partial_modification:
            logger.info(f"Partial modification detected: '{data.message}' - will skip confirmation and update directly")
    
    # Check if message is a confirmation response
    confirmation_keywords = ["có", "yes", "ok", "đúng", "đồng ý", "tiếp tục", "xác nhận", "được", "okay"]
    message_lower = data.message.lower().strip()
    is_confirmation = any(keyword in message_lower for keyword in confirmation_keywords) and len(message_lower.split()) <= 3
    
    # Check if last assistant message was asking for confirmation
    last_assistant_message = None
    if conversation_history:
        for msg in reversed(conversation_history):
            if msg.get("role") == "assistant":
                last_assistant_message = msg.get("content", "")
                break
    
    is_confirming_previous = is_confirmation and last_assistant_message and "Bạn xác nhận chứ" in last_assistant_message
    
    logger.info(f"Planning check - has_city: {has_city} ({city}), has_budget: {has_budget} ({budget_vnd}), has_duration: {has_duration} ({duration_days}), is_confirmation: {is_confirmation}, is_confirming_previous: {is_confirming_previous}, is_partial_modification: {is_partial_modification}")
    
    # If this is a partial modification, skip confirmation and proceed directly to update
    if is_partial_modification and previous_itinerary:
        logger.info(f"Partial modification detected - skipping confirmation and proceeding to update itinerary")
        # Continue to create/update itinerary below
    # If user is confirming previous confirmation request, proceed to create itinerary
    elif is_confirming_previous and has_city and has_duration and (has_budget or has_budget_from_profile):
        logger.info(f"User confirmed. Proceeding to create itinerary.")
        # Continue to create itinerary below
    # If we don't have all 3 required items (city, duration, budget), ask for clarification
    elif not (has_city and has_duration and (has_budget or has_budget_from_profile)):
        logger.warning(f"Insufficient info for planning. Asking for clarification. city={city}, budget={budget_vnd}, duration={duration_days}")
        # Add budget_min and budget_max to extracted_data for confirmation message
        if user_profile:
            extracted_data["budget_min"] = user_profile.get("budget_min")
            extracted_data["budget_max"] = user_profile.get("budget_max")
        
        clarification_message = await llm_agent.generate_confirmation_message(
            extracted_data,
            conversation_history,
            user_profile
        )
        
        assistant_message_id = str(uuid4())
        db.add_message(assistant_message_id, conversation_id, "assistant", clarification_message)
        
        return {
            "ok": True,
            "requires_clarification": True,
            "clarification_message": clarification_message,
            "conversation_id": conversation_id,
            "extracted_data": extracted_data
        }
    # If we have all 3 items but user hasn't confirmed yet and it's not a partial modification, ask for confirmation
    elif not is_confirming_previous and not is_partial_modification:
        logger.info(f"All info available but not confirmed yet. Asking for confirmation.")
        # Add budget_min and budget_max to extracted_data for confirmation message
        if user_profile:
            extracted_data["budget_min"] = user_profile.get("budget_min")
            extracted_data["budget_max"] = user_profile.get("budget_max")
        
        confirmation_message = await llm_agent.generate_confirmation_message(
            extracted_data,
            conversation_history,
            user_profile
        )
        
        assistant_message_id = str(uuid4())
        db.add_message(assistant_message_id, conversation_id, "assistant", confirmation_message)
        
        return {
            "ok": True,
            "requires_confirmation": True,
            "confirmation_message": confirmation_message,
            "conversation_id": conversation_id,
            "extracted_data": extracted_data
        }
    
    logger.info(f"Sufficient info and confirmed. Proceeding to create itinerary.")
    
    # Convert extracted data to constraints format
    # Calculate dates if duration is provided but dates are not
    date_start = date_range.get("start")
    date_end = date_range.get("end")
    
    if not date_start and duration_days:
        # Default to starting tomorrow
        # date_end should be date_start + duration_days - 1 (e.g., 4 days = day 1, 2, 3, 4)
        # If user says "4 ngày 3 đêm", that means 4 days total: day 1, 2, 3, 4
        start_date = (datetime.now() + timedelta(days=1)).date()
        date_start = start_date.isoformat()
        # start_date is already a date object, so no need to call .date() again
        date_end = (start_date + timedelta(days=duration_days - 1)).isoformat()
        logger.info(f"Calculated dates from duration: date_start={date_start}, date_end={date_end}, duration_days={duration_days}")
    
    if not date_start:
        date_start = (datetime.now() + timedelta(days=1)).date().isoformat()
        date_end = (datetime.now() + timedelta(days=2)).date().isoformat()
        logger.info(f"Using default dates: date_start={date_start}, date_end={date_end}")
    
    hard_constraints = {
        "destination": city,
        "date_start": date_start,
        "date_end": date_end,
        "budget_vnd": budget_vnd or 5000000,  # Default 5M if not provided
    }
    
    # Ensure all soft_constraints fields have valid string values (not None)
    # Extract and validate spending_style
    spending_style = None
    if preferences and preferences.get("style"):
        spending_style = preferences.get("style")
    if not spending_style or spending_style not in ["budget", "balanced", "premium"]:
        spending_style = "balanced"
    
    # Extract and validate energy
    # Priority: extracted_data > user_configs > default
    energy = None
    if extracted_data and extracted_data.get("energy"):
        energy = extracted_data.get("energy")
    elif user_configs and user_configs.get("energy_level"):
        energy = user_configs.get("energy_level")
    if not energy or energy not in ["low", "medium", "high"]:
        energy = "medium"
    
    # Build soft_constraints with all required fields
    soft_constraints = {
        "spending_style": spending_style,  # Always a valid string
        "energy": energy,  # Always a valid string
        "travel_style": "balanced",  # Default value
        "pace": "moderate",  # Default value
        "interests": []  # Empty list by default
    }
    
    # Add interests from extracted preferences if available
    if preferences:
        if preferences.get("food"):
            soft_constraints["interests"].append(preferences["food"])
        if preferences.get("activities"):
            soft_constraints["interests"].append(preferences["activities"])
    
    # Add interests from user_configs (preferences_json) if available
    if user_configs and user_configs.get("preferences_json"):
        try:
            user_preferences = []
            if isinstance(user_configs["preferences_json"], str):
                user_preferences = json.loads(user_configs["preferences_json"])
            elif isinstance(user_configs["preferences_json"], list):
                user_preferences = user_configs["preferences_json"]
            
            if user_preferences:
                soft_constraints["interests"].extend(user_preferences)
                logger.info(f"Added {len(user_preferences)} preferences from user configs: {user_preferences}")
        except Exception as e:
            logger.error(f"Error parsing preferences_json from user configs: {e}")
    
    # Extract preferences from conversation history and merge
    if conversation_history and len(conversation_history) > 0:
        # Extract preferences from all previous user messages
        conversation_preferences = await llm_agent.extract_preferences_from_history(conversation_history)
        if conversation_preferences:
            # Merge interests
            if conversation_preferences.get("interests"):
                soft_constraints["interests"].extend(conversation_preferences["interests"])
            
            # Merge other preferences if not already set
            if not soft_constraints.get("spending_style") or soft_constraints["spending_style"] == "balanced":
                if conversation_preferences.get("spending_style"):
                    soft_constraints["spending_style"] = conversation_preferences["spending_style"]
            
            if not soft_constraints.get("energy") or soft_constraints["energy"] == "medium":
                if conversation_preferences.get("energy"):
                    soft_constraints["energy"] = conversation_preferences["energy"]
            
            if conversation_preferences.get("travel_style"):
                soft_constraints["travel_style"] = conversation_preferences["travel_style"]
            
            # Dedupe interests
            soft_constraints["interests"] = list(set(soft_constraints["interests"]))
    
    logger.info(f"Created soft_constraints: {soft_constraints}")
    
    # Generate plan
    planner_request = {
        "user_id": user_id,
        "hard_constraints": hard_constraints,
        "soft_constraints": soft_constraints,
        "conversation_id": conversation_id,
        "conversation_history": conversation_history,  # Pass conversation history to planner
    }
    
    try:
        itinerary = None
        updated_itinerary = None
        
        # Check if duration has changed (increased)
        previous_duration = None
        if previous_itinerary:
            previous_days = previous_itinerary.get("days", [])
            previous_duration = len(previous_days)
        
        # Detect if user is specifying specific days (e.g., "ngày 3,4" or "vào ngày 2,3")
        # This means they want to add activities to specific days, NOT change total duration
        message_lower = data.message.lower()
        specific_days_pattern = re.search(r'(?:vào\s+)?ngày\s+(\d+(?:\s*[,và]\s*\d+)*)', message_lower)
        is_specific_days_request = specific_days_pattern is not None
        
        duration_changed = False
        if previous_duration and duration_days:
            # If user is specifying specific days (e.g., "ngày 3,4"), don't treat it as duration change
            if is_specific_days_request:
                logger.info(f"User specified specific days in request - keeping original duration: {previous_duration} days")
                duration_changed = False
                # Reset duration_days to previous duration to avoid recreating itinerary
                duration_days = previous_duration
            else:
                duration_changed = duration_days != previous_duration
                if duration_changed:
                    logger.info(f"Duration changed from {previous_duration} days to {duration_days} days - will recreate itinerary")
        
        # If modification request with previous itinerary and duration hasn't increased, add activities instead of recreating
        # Also handle partial modifications (adding activities to specific days)
        if (is_modification or is_partial_modification) and previous_itinerary and not duration_changed:
            logger.info("Modification request detected - adding activities to existing itinerary")
            
            # Use add_activities_to_itinerary to keep existing plan and add new activities
            updated_itinerary = await planner.add_activities_to_itinerary(
                previous_itinerary,
                planner_request,
                data.message
            )
            
            # Transform back to frontend format (itinerary from add_activities is in planner format)
            transformed_itinerary = _transform_itinerary_for_frontend(
                updated_itinerary, city, duration_days, budget_vnd
            )
            itinerary = updated_itinerary  # Use for description generation
        else:
            # Create new itinerary (either new request or duration changed)
            if duration_changed:
                logger.info(f"Recreating itinerary due to duration change: {previous_duration} -> {duration_days} days")
            else:
                logger.info("Creating new itinerary")
            
            itinerary = await planner.plan(planner_request)
            
            # Transform itinerary to frontend format
            transformed_itinerary = _transform_itinerary_for_frontend(
                itinerary, city, duration_days, budget_vnd
            )
        
        # Save assistant message with itinerary
        assistant_message_id = str(uuid4())
        # Get budget_min and budget_max from user profile for budget range display
        budget_min = None
        budget_max = None
        if user_profile:
            budget_min = user_profile.get("budget_min")
            budget_max = user_profile.get("budget_max")
        
        itinerary_description = await llm_agent.generate_itinerary_description(
            itinerary,
            {
                "city": city, 
                "budget": budget_vnd, 
                "duration": duration_days,
                "budget_min": budget_min,
                "budget_max": budget_max
            }
        )
        
        db.add_message(
            assistant_message_id,
            conversation_id,
            "assistant",
            itinerary_description,
            itinerary_data=transformed_itinerary
        )
        
        # Update conversation title if needed
        if city:
            new_title = f"{city} - {duration_days} ngày" if duration_days else city
            db.update_conversation_title(conversation_id, new_title)
        
        return {
            "ok": True,
            "itinerary": transformed_itinerary,
            "conversation_id": conversation_id,
            "destination": city,
            "duration": duration_days,
            "budget": budget_vnd
        }
    except Exception as e:
        error_message = f"Xin lỗi, đã có lỗi xảy ra khi tạo lịch trình: {str(e)}"
        assistant_message_id = str(uuid4())
        db.add_message(assistant_message_id, conversation_id, "assistant", error_message)
        
        raise HTTPException(500, detail=error_message)


# --------------------------
# DIRECT PLANNING ROUTE (for advanced use cases with pre-extracted constraints)
# --------------------------
@router.post("/direct", tags=["planner"])
async def plan_trip_direct(data: PlanRequest, authorization: Optional[str] = Header(None)):

    user_id = get_user_id(authorization)

    # Inject user ID into planner request
    req = {
        "user_id": user_id,
        "hard_constraints": data.hard_constraints,
        "soft_constraints": data.soft_constraints,
        "conversation_id": data.conversation_id,
    }

    # Orchestrator generates a complete itinerary
    output = await planner.plan(req)

    # Save message to conversation history
    db.add_message(
        message_id=str(output["itinerary_id"]),
        conversation_id=data.conversation_id,
        role="assistant",
        content="Itinerary generated",
        itinerary_data=output,
    )

    return {"status": "ok", "itinerary": output}


# --------------------------
# Travel Time API Endpoint
# --------------------------
@router.get("/travel-time", tags=["planner"])
async def get_travel_time(
    origin: str,  # Format: "lat,lng"
    destination: str,  # Format: "lat,lng"
    mode: str = "driving",  # driving, walking, bicycling, transit
    authorization: Optional[str] = Header(None)
):
    """
    Get travel time and distance between two points using Google Maps Distance Matrix API.
    
    Args:
        origin: Origin coordinates in format "lat,lng"
        destination: Destination coordinates in format "lat,lng"
        mode: Transportation mode (driving, walking, bicycling, transit)
    
    Returns:
        {
            "travelTime": int,  # seconds
            "distance": int     # meters
        }
    """
    try:
        # Parse coordinates
        origin_parts = origin.split(",")
        dest_parts = destination.split(",")
        
        if len(origin_parts) != 2 or len(dest_parts) != 2:
            raise HTTPException(400, "Invalid coordinate format. Use 'lat,lng'")
        
        origin_coords = {"lat": float(origin_parts[0].strip()), "lng": float(origin_parts[1].strip())}
        dest_coords = {"lat": float(dest_parts[0].strip()), "lng": float(dest_parts[1].strip())}
        
        # Validate mode
        valid_modes = ["driving", "walking", "bicycling", "transit"]
        if mode not in valid_modes:
            mode = "driving"  # Default to driving
        
        # Use Distance Matrix API (single pair)
        results = maps_service.get_distance_matrix(
            origins=[origin_coords],
            destinations=[dest_coords],
            mode=mode
        )
        
        if not results or len(results) == 0:
            raise HTTPException(500, "Failed to calculate travel time")
        
        result = results[0]
        
        return {
            "travelTime": result["travelTime"],  # seconds
            "distance": result["distance"]        # meters
        }
        
    except ValueError as e:
        raise HTTPException(400, f"Invalid coordinate values: {str(e)}")
    except Exception as e:
        logger.error(f"Error calculating travel time: {e}")
        raise HTTPException(500, f"Error calculating travel time: {str(e)}")
