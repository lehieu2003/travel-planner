# backend/app/orchestrator/planner_orchestrator.py

import asyncio
import re
import unicodedata
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta

from app.db.sqlite_memory import SQLiteMemory
from app.agents.activities_agent import ActivitiesAgent
from app.agents.accommodation_agent import AccommodationAgent
from app.agents.transportation_agent import TransportationAgent
from app.agents.map_agent import MapAgent
from app.services.google_maps_service import GoogleMapsService
from app.services.place_service import PlaceService
from app.core.logger import logger

from app.models.preference_models import (
    UserPreferenceBundle,
    SoftConstraints,
    HardConstraints,
    LongTermPreferences,
    ShortTermPreferences,
)


class PlannerOrchestrator:

    def __init__(self):
        self.db = SQLiteMemory()

        # AGENTS
        self.activities_agent = ActivitiesAgent()
        self.accom_agent = AccommodationAgent()
        self.transport_agent = TransportationAgent()
        self.map_agent = MapAgent()
        self.maps_service = GoogleMapsService()
        self.place_service = PlaceService()

    # -----------------------------------------------------------
    # Helper: Check if name contains Vietnamese characters
    # -----------------------------------------------------------
    def _has_vietnamese_chars(self, text: str) -> bool:
        """
        Check if text contains Vietnamese characters (accented letters)
        Vietnamese characters include: àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ
        """
        if not text:
            return False
        
        # Vietnamese accented characters ranges
        vietnamese_chars = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ')
        
        # Check if any character in text is Vietnamese
        return any(char in vietnamese_chars for char in text)
    
    # -----------------------------------------------------------
    # Helper: Normalize Vietnamese text for deduplication
    # -----------------------------------------------------------
    def _normalize_vietnamese_text(self, text: str) -> str:
        """
        Normalize Vietnamese text for deduplication.
        Removes accents and converts to lowercase.
        
        Example:
            "Phở Bò" -> "pho bo"
            "Cà Phê Trứng" -> "ca phe trung"
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Normalize Unicode (NFD = Canonical Decomposition)
        text = unicodedata.normalize("NFD", text)
        
        # Remove combining diacritical marks (accents)
        text = re.sub(r'[\u0300-\u036f]', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    # -----------------------------------------------------------
    # Convert user memory into Pydantic objects
    # -----------------------------------------------------------
    def _load_user_memory(self, user_id: str):

        long_raw = self.db.get_long_memory(user_id) or {}
        short_raw = {}  # per-conversation memory (set later in conversation)

        long_term = LongTermPreferences(**long_raw) if long_raw else LongTermPreferences()
        short_term = ShortTermPreferences(**short_raw)

        return long_term, short_term

    # -----------------------------------------------------------
    # Merge User Preferences from request + memory
    # -----------------------------------------------------------
    def _build_preference_bundle(self, planner_request: dict, user_id: str):

        hard = HardConstraints(**planner_request["hard_constraints"])
        soft = SoftConstraints(**planner_request.get("soft_constraints", {}))

        long_term, short_term = self._load_user_memory(user_id)

        # Get user profile to retrieve energy_level from database
        # Priority: explicit request > user profile > default
        user_profile = self.db.get_user_by_id(int(user_id))
        
        # Check if energy was explicitly set in request (not default)
        energy_explicitly_set = (
            soft.energy and 
            soft.energy != "medium" and 
            soft.energy in ["low", "high"]
        )
        
        if not energy_explicitly_set and user_profile and user_profile.get("energy_level"):
            # Use user profile energy if not explicitly overridden
            db_energy = user_profile["energy_level"]
            if db_energy in ["low", "medium", "high"]:
                soft.energy = db_energy
                logger.info(f"Using energy level from user profile (user_id={user_id}): {db_energy}")
        elif not soft.energy:
            # If no user profile energy and no energy in request, default to medium
            soft.energy = "medium"
            logger.info(f"No energy level found, using default: medium")
        elif energy_explicitly_set:
            logger.info(f"Using explicitly set energy level from request: {soft.energy}")

        # Auto-merge long-term preferences into soft constraints
        if long_term.food_preferences:
            soft.interests.extend(long_term.food_preferences)
        if long_term.activity_preferences:
            soft.interests.extend(long_term.activity_preferences)

        soft.interests = list(set(soft.interests))  # dedupe

        return UserPreferenceBundle(
            hard=hard,
            soft=soft,
            long_term=long_term,
            short_term=short_term
        )

    # -----------------------------------------------------------
    # Core itinerary pipeline
    # -----------------------------------------------------------
    async def plan(self, planner_request: dict) -> dict:

        request_id = str(uuid4())
        user_id = planner_request["user_id"]
        planner_request["request_id"] = request_id

        # 1. Build merged preference object
        pref_bundle = self._build_preference_bundle(planner_request, user_id)
        planner_request["preference_bundle"] = pref_bundle

        hard = pref_bundle.hard
        soft = pref_bundle.soft

        total_budget = hard.budget_vnd or 5_000_000

        # Spending-style dynamic budget
        if soft.spending_style == "budget":
            hotel_ratio, activity_ratio, food_ratio = 0.30, 0.10, 0.15
        elif soft.spending_style == "premium":
            hotel_ratio, activity_ratio, food_ratio = 0.50, 0.30, 0.20
        else:
            hotel_ratio, activity_ratio, food_ratio = 0.40, 0.20, 0.15

        budget_alloc = {
            "hotel": round(total_budget * hotel_ratio),
            "activities": round(total_budget * activity_ratio),
            "food": round(total_budget * food_ratio),
            "transport": round(total_budget * (1 - hotel_ratio - activity_ratio - food_ratio)),
        }

        # ---------------------------------------------------------
        # 2. Run Agents in parallel (Activities / Hotels / Flights)
        # ---------------------------------------------------------
        act_task = asyncio.create_task(self.activities_agent.handle(planner_request))
        # We inject ranked activities BACK into planner request
        # so accommodation agent knows zone
        await asyncio.sleep(0)

        activities = await act_task
        ranked_activities = activities["payload"]["ranked"]
        logger.info(f"Activities agent returned {len(ranked_activities)} activities")
        planner_request["ranked_activities"] = ranked_activities

        # Now accommodation + transport can run
        accom_task = asyncio.create_task(self.accom_agent.handle(planner_request))
        trans_task = asyncio.create_task(self.transport_agent.handle(planner_request))

        accom_resp, trans_resp = await asyncio.gather(accom_task, trans_task)

        best_hotel = accom_resp["payload"][0] if accom_resp["payload"] else None

        # ---------------------------------------------------------
        # 3. Get travel times for top activities from the chosen hotel
        # ---------------------------------------------------------
        scored_with_travel = []

        if best_hotel and best_hotel.get("coordinates"):
            # Separate activities with and without coordinates
            activities_with_coords = []
            activities_without_coords = []
            
            for act in ranked_activities[:10]:
                if act.get("coordinates") and act["coordinates"].get("lat") and act["coordinates"].get("lng"):
                    activities_with_coords.append(act)
                else:
                    # Add activity without travel time calculation
                    act["travel_time_min"] = 0
                    activities_without_coords.append(act)
            
            # Calculate travel times for activities with coordinates
            if activities_with_coords:
                legs = []
                for act in activities_with_coords:
                    legs.append({
                        "origin": best_hotel["coordinates"],
                        "dest": act["coordinates"],
                        "mode": "driving"
                    })

                directions = await self.map_agent.handle({
                    "request_id": request_id,
                    "params": {"legs": legs}
                })

                legs_info = directions["payload"]["legs"]

                # Re-score activities with travel time using Hybrid Scoring Algorithm
                from app.utils.scoring import score_activity_with_hybrid_algorithm
                from app.models.preference_models import compute_preference_score
                from app.core.llm import gpt_preference_score
                
                for act, leg in zip(activities_with_coords, legs_info):
                    travel_time_min = leg["duration_min"]
                    act["travel_time_min"] = travel_time_min
                    
                    # Re-calculate score with travel time using Hybrid Scoring Algorithm
                    # Get preference score components (already calculated in activities_agent)
                    pref_score_components = act.get("pref_score_components", {})
                    user_fit = pref_score_components.get("final_score", act.get("gpt_pref_score", 0.5))
                    
                    # Re-score with travel time
                    algo_score = score_activity_with_hybrid_algorithm(
                        place=act,
                        preference_score=user_fit,
                        energy=soft.energy,
                        activity_budget=planner_request.get("activity_budget", 1_000_000),
                        travel_time_min=travel_time_min
                    )
                    act["algo_score"] = algo_score
                    scored_with_travel.append(act)
            
            # Add activities without coordinates
            scored_with_travel.extend(activities_without_coords)
            
            # Add remaining activities (beyond top 10) without travel time
            for act in ranked_activities[10:]:
                act["travel_time_min"] = 0
                scored_with_travel.append(act)
        else:
            # No hotel, so no travel time calculation needed
            for act in ranked_activities:
                act["travel_time_min"] = 0
            scored_with_travel = ranked_activities

        # ---------------------------------------------------------
        # 4. Build day-by-day itinerary
        # ---------------------------------------------------------
        days = []
        start = datetime.fromisoformat(hard.date_start)
        end = datetime.fromisoformat(hard.date_end)
        total_days = (end - start).days + 1

        logger.info(f"Building itinerary for {total_days} days, {len(scored_with_travel)} activities available")

        # Separate activities by category and deduplicate by name (normalized)
        # Only keep places with Vietnamese names to avoid duplicates
        seen_names = set()  # Normalized names
        food_activities = []
        drink_activities = []
        other_activities = []
        
        for act in scored_with_travel:
            name = act.get("name", "").strip()
            if not name:
                continue
            
            # Only keep places with Vietnamese names
            if not self._has_vietnamese_chars(name):
                logger.debug(f"Skipping place with non-Vietnamese name: {name}")
                continue
            
            # Normalize name for deduplication
            normalized_name = self._normalize_vietnamese_text(name)
            
            # Skip if we've seen this normalized name before
            if normalized_name in seen_names:
                continue
            
            seen_names.add(normalized_name)
            
            category = act.get("category")
            if category == "food":
                food_activities.append(act)
            elif category == "drink" or category == "coffee":  # Backward compatibility
                drink_activities.append(act)
            else:
                other_activities.append(act)

        logger.info(f"Separated activities: {len(food_activities)} food, {len(drink_activities)} drink, {len(other_activities)} other activities")
        
        # Debug: Check for duplicates in food_activities itself
        food_names_normalized = [self._normalize_vietnamese_text(f.get("name", "")) for f in food_activities]
        food_names_set = set(food_names_normalized)
        if len(food_names_normalized) != len(food_names_set):
            duplicates = len(food_names_normalized) - len(food_names_set)
            logger.warning(f"WARNING: Found {duplicates} duplicate food names in food_activities list!")
            # Find and log duplicate names
            from collections import Counter
            name_counts = Counter(food_names_normalized)
            duplicates_list = [name for name, count in name_counts.items() if count > 1]
            logger.warning(f"Duplicate food names: {duplicates_list[:10]}")  # Show first 10
        
        # Debug: Log unique food names to check diversity
        if food_activities:
            unique_food_names = [f.get("name", "") for f in food_activities[:20]]  # First 20
            logger.info(f"Sample food names (first 20): {unique_food_names}")
            logger.info(f"Total unique food names (normalized): {len(food_names_set)}")

        # Energy-based daily time budget
        if soft.energy == "low":
            daily_minutes = 4 * 60
            max_other_activities_per_day = 2  # Low energy: fewer activities
        elif soft.energy == "high":
            daily_minutes = 9 * 60
            max_other_activities_per_day = 6  # High energy: more activities
        else:
            daily_minutes = 6 * 60
            max_other_activities_per_day = 4  # Medium energy: moderate activities

        logger.info(f"Daily minutes budget: {daily_minutes} minutes ({daily_minutes // 60} hours), max {max_other_activities_per_day} other activities per day")

        # Calculate minimum activities needed per day to ensure all days have activities
        min_activities_per_day = max(1, len(other_activities) // total_days) if other_activities else 0
        logger.info(f"Minimum activities per day: {min_activities_per_day} (total activities: {len(other_activities)}, total days: {total_days})")

        # Track indices for each category
        food_idx = 0
        drink_idx = 0
        other_idx = 0
        
        # Track ALL food and drink used across ALL days to prevent duplicates between days
        # Use normalized names for deduplication
        all_used_food_names = set()  # Normalized food names
        all_used_drink_names = set()  # Normalized drink names
        logger.info(f"Total food activities available: {len(food_activities)}, drink: {len(drink_activities)}")
        
        # Validate we have enough food and drink
        required_food = total_days * 3  # 3 meals per day
        required_drink = total_days * 1  # 1-2 per day minimum
        
        if len(food_activities) < required_food:
            logger.error(
                f"INSUFFICIENT FOOD: Only {len(food_activities)} food places available "
                f"(required: {required_food} for {total_days} days)"
            )
        if len(drink_activities) < required_drink:
            logger.error(
                f"INSUFFICIENT DRINK: Only {len(drink_activities)} drink places available "
                f"(required: {required_drink} for {total_days} days)"
            )

        # Helper function to get next food activity (with cycling if needed)
        def get_next_food(day_activity_names_set, used_across_days_set):
            """Get next food activity, ensuring no duplicates within day or across days (using normalized names)"""
            nonlocal food_idx  # Use food_idx from outer scope
            attempts = 0
            max_attempts = len(food_activities) * 3  # Increase attempts to find unique food
            
            while attempts < max_attempts:
                if food_idx >= len(food_activities):
                    # Cycle back to beginning if we've exhausted the list
                    food_idx = 0
                
                food = food_activities[food_idx]
                food_name = food.get("name", "").strip()
                if not food_name:
                    food_idx += 1
                    attempts += 1
                    continue
                
                # Normalize name for comparison
                normalized_food_name = self._normalize_vietnamese_text(food_name)
                
                # Skip if already added to this day OR used in previous days
                if normalized_food_name in day_activity_names_set or normalized_food_name in used_across_days_set:
                    food_idx += 1
                    attempts += 1
                    continue
                
                # Found unique food - mark it as used and return
                used_across_days_set.add(normalized_food_name)
                current_idx = food_idx
                food_idx += 1  # Move to next for next call
                logger.info(f"✓ Found unique food at index {current_idx}: '{food_name}' (normalized: '{normalized_food_name}') - Total used across all days: {len(used_across_days_set)}")
                return food, current_idx
            
            # If we exhausted all attempts, log error
            # This should NOT happen if we have enough food (days * 3)
            logger.error(
                f"CRITICAL: Could not find unique food after {max_attempts} attempts. "
                f"Total available: {len(food_activities)}, already used: {len(used_across_days_set)}, "
                f"required: {total_days * 3}"
            )
            
            # Try one more time: scan ALL food_activities to find ANY unused food
            # This is a more thorough search
            for idx, food in enumerate(food_activities):
                food_name = food.get("name", "").strip()
                if not food_name:
                    continue
                normalized_food_name = self._normalize_vietnamese_text(food_name)
                
                # CRITICAL: Must check BOTH day_activity_names_set AND used_across_days_set
                if normalized_food_name not in day_activity_names_set and normalized_food_name not in used_across_days_set:
                    # Found unused food - mark as used and return
                    used_across_days_set.add(normalized_food_name)
                    food_idx = (idx + 1) % len(food_activities)
                    logger.warning(f"Found unused food at index {idx} after exhaustive search: {food_name}")
                    return food, idx
            
            # If still no unused food found, this is a critical error
            # Return None and let the caller handle it
            logger.error(
                f"FATAL: No unused food found! Total food: {len(food_activities)}, "
                f"Used: {len(used_across_days_set)}, Day activities: {len(day_activity_names_set)}"
            )
            return None, 0
        
        # Helper function to get next drink activity (with cycling if needed)
        def get_next_drink(day_activity_names_set, used_across_days_set):
            """Get next drink activity, ensuring no duplicates within day or across days (using normalized names)"""
            nonlocal drink_idx  # Use drink_idx from outer scope
            attempts = 0
            max_attempts = len(drink_activities) * 3  # Increase attempts to find unique drink
            
            while attempts < max_attempts:
                if drink_idx >= len(drink_activities):
                    # Cycle back to beginning if we've exhausted the list
                    drink_idx = 0
                
                drink = drink_activities[drink_idx]
                drink_name = drink.get("name", "").strip()
                if not drink_name:
                    drink_idx += 1
                    attempts += 1
                    continue
                
                # Normalize name for comparison
                normalized_drink_name = self._normalize_vietnamese_text(drink_name)
                
                # Skip if already added to this day OR used in previous days
                if normalized_drink_name in day_activity_names_set or normalized_drink_name in used_across_days_set:
                    drink_idx += 1
                    attempts += 1
                    continue
                
                # Found unique drink - mark it as used and return
                used_across_days_set.add(normalized_drink_name)
                current_idx = drink_idx
                drink_idx += 1  # Move to next for next call
                logger.debug(f"Found unique drink at index {current_idx}: {drink_name} (total used: {len(used_across_days_set)})")
                return drink, current_idx
            
            # If we exhausted all attempts, log error
            # This should NOT happen if we have enough drink (days * 1)
            logger.error(
                f"CRITICAL: Could not find unique drink after {max_attempts} attempts. "
                f"Total available: {len(drink_activities)}, already used: {len(used_across_days_set)}, "
                f"required: {total_days * 1}"
            )
            
            # Try one more time: scan ALL drink_activities to find ANY unused drink
            # This is a more thorough search
            for idx, drink in enumerate(drink_activities):
                drink_name = drink.get("name", "").strip()
                if not drink_name:
                    continue
                normalized_drink_name = self._normalize_vietnamese_text(drink_name)
                
                # CRITICAL: Must check BOTH day_activity_names_set AND used_across_days_set
                if normalized_drink_name not in day_activity_names_set and normalized_drink_name not in used_across_days_set:
                    # Found unused drink - mark as used and return
                    used_across_days_set.add(normalized_drink_name)
                    drink_idx = (idx + 1) % len(drink_activities)
                    logger.warning(f"Found unused drink at index {idx} after exhaustive search: {drink_name}")
                    return drink, idx
            
            # If still no unused drink found, this is a critical error
            # Return None and let the caller handle it
            logger.error(
                f"FATAL: No unused drink found! Total drink: {len(drink_activities)}, "
                f"Used: {len(used_across_days_set)}, Day activities: {len(day_activity_names_set)}"
            )
            return None, 0

        for d in range(total_days):
            date = (start + timedelta(days=d)).date().isoformat()
            remain = daily_minutes
            segments = []
            # Track activities added to this day to prevent duplicates (using normalized names)
            day_activity_names = set()  # Normalized names

            # 1. Add breakfast (07:00-09:00) - ALWAYS add, Stage 4: Meal Scheduling (Strict)
            logger.info(f"Day {d + 1}: Starting to add breakfast. Already used food: {len(all_used_food_names)}/{len(food_activities)}")
            breakfast, food_idx = get_next_food(day_activity_names, all_used_food_names)
            if breakfast:
                breakfast_name_normalized = self._normalize_vietnamese_text(breakfast.get("name", ""))
                logger.info(f"Day {d + 1}: Selected breakfast '{breakfast.get('name')}' (normalized: '{breakfast_name_normalized}')")
                food_duration = breakfast.get("recommended_duration_min", 75)
                travel_time = breakfast.get("travel_time_min", 0) or 0
                duration = food_duration + travel_time + 30
                
                # Ensure breakfast is scheduled in 07:00-09:00 time slot
                segments.append({
                    "type": "activity",
                    "name": breakfast.get("name", ""),
                    "address": breakfast.get("address"),
                    "duration_min": food_duration,
                    "travel_time_min": travel_time if travel_time > 0 else None,
                    "estimated_cost_vnd": breakfast.get("estimated_cost_vnd", 0),
                    "category": "food",
                    "meal_type": "breakfast",
                    "meal_time_slot": "07:00-09:00",  # Stage 4: Strict meal time slot
                    "rating": breakfast.get("rating"),
                    "votes": breakfast.get("votes", 0),
                    "price_level": breakfast.get("price_level"),
                    "coordinates": breakfast.get("coordinates"),
                    "algo_score": breakfast.get("algo_score", 0),
                    "description": breakfast.get("description", ""),
                })
                day_activity_names.add(self._normalize_vietnamese_text(breakfast.get("name", "")))
                remain -= duration
                # food_idx already incremented in get_next_food()
                logger.info(f"Day {d + 1}: Added breakfast (07:00-09:00) - {breakfast.get('name')} (food_idx: {food_idx}, total used: {len(all_used_food_names)})")

            # 2. Add other activities based on energy level
            other_count = 0
            skipped_count = 0
            max_skips = 10  # Limit number of skips to prevent exhausting all activities
            
            # Ensure each day gets at least min_activities_per_day if possible
            while other_idx < len(other_activities) and other_count < max_other_activities_per_day:
                act = other_activities[other_idx]
                act_name = act.get("name", "").strip()
                if not act_name:
                    other_idx += 1
                    continue
                
                normalized_act_name = self._normalize_vietnamese_text(act_name)
                
                # Skip if already added to this day
                if normalized_act_name in day_activity_names:
                    other_idx += 1
                    continue
                
                activity_duration = act.get("recommended_duration_min", 60)
                travel_time = act.get("travel_time_min", 0) or 0
                duration = activity_duration + travel_time + 30

                # If we haven't reached minimum and this is one of the last days, be more lenient
                needs_minimum = (other_count < min_activities_per_day) and (d >= total_days - 2)  # Last 2 days need minimum
                
                if duration <= remain or (needs_minimum and remain > 30):
                    # If it doesn't fit but we need minimum, add it with reduced duration
                    actual_duration = min(activity_duration, remain - 30) if duration > remain and needs_minimum else activity_duration
                    
                    segments.append({
                        "type": "activity",
                        "name": act.get("name", ""),
                        "address": act.get("address"),
                        "duration_min": actual_duration if actual_duration > 0 else activity_duration,
                        "travel_time_min": travel_time if travel_time > 0 else None,
                        "estimated_cost_vnd": act.get("estimated_cost_vnd", 0),
                        "category": act.get("category"),
                        "rating": act.get("rating"),
                        "coordinates": act.get("coordinates"),
                        "algo_score": act.get("algo_score", 0),
                    })
                    day_activity_names.add(normalized_act_name)
                    remain -= min(duration, remain) if duration > remain and needs_minimum else duration
                    other_count += 1
                    other_idx += 1
                    skipped_count = 0  # Reset skip counter when we add an activity
                    
                    # If we added with reduced duration, break to preserve remaining time
                    if duration > remain and needs_minimum:
                        logger.info(f"Day {d + 1}: Added activity with reduced duration to meet minimum - {act.get('name')}")
                        break
                else:
                    # Activity doesn't fit, skip it but limit skips to preserve activities for other days
                    skipped_count += 1
                    if skipped_count >= max_skips:
                        # Too many skips, break to preserve remaining activities for other days
                        logger.info(f"Day {d + 1}: Skipped {skipped_count} activities that don't fit, preserving remaining for other days")
                        break
                    other_idx += 1
                    if other_idx >= len(other_activities):
                        break

            # 3. Add lunch (11:30-13:30) - ALWAYS add, Stage 4: Meal Scheduling (Strict)
            # CRITICAL: Ensure there's at least 1 activity or drink between breakfast and lunch
            # Check if last segment is food (breakfast)
            last_segment_is_food = len(segments) > 0 and segments[-1].get("category") == "food"
            if last_segment_is_food:
                # Need to add activity or drink before lunch
                logger.info(f"Day {d + 1}: Last segment is food, adding activity/drink before lunch")
                
                # Try to add a drink first (shorter duration)
                if remain > 60:
                    drink_before_lunch, drink_idx_temp = get_next_drink(day_activity_names, all_used_drink_names)
                    if drink_before_lunch:
                        drink_duration = drink_before_lunch.get("recommended_duration_min", 60)
                        travel_time = drink_before_lunch.get("travel_time_min", 0) or 0
                        duration = drink_duration + travel_time + 30
                        
                        if duration <= remain:
                            segments.append({
                                "type": "activity",
                                "name": drink_before_lunch.get("name", ""),
                                "address": drink_before_lunch.get("address"),
                                "duration_min": drink_duration,
                                "travel_time_min": travel_time if travel_time > 0 else None,
                                "estimated_cost_vnd": drink_before_lunch.get("estimated_cost_vnd", 0),
                                "category": "drink",
                                "rating": drink_before_lunch.get("rating"),
                                "votes": drink_before_lunch.get("votes", 0),
                                "price_level": drink_before_lunch.get("price_level"),
                                "coordinates": drink_before_lunch.get("coordinates"),
                                "algo_score": drink_before_lunch.get("algo_score", 0),
                                "description": drink_before_lunch.get("description", ""),
                            })
                            day_activity_names.add(self._normalize_vietnamese_text(drink_before_lunch.get("name", "")))
                            remain -= duration
                            logger.info(f"Day {d + 1}: Added drink before lunch - {drink_before_lunch.get('name')}")
                
                # If no drink added, try to add a short activity
                if last_segment_is_food and len(segments) > 0 and segments[-1].get("category") == "food":
                    # Still need activity/drink, try short activity
                    if other_idx < len(other_activities) and remain > 30:
                        act = other_activities[other_idx]
                        act_name = act.get("name", "").strip()
                        if act_name:
                            normalized_act_name = self._normalize_vietnamese_text(act_name)
                            if normalized_act_name not in day_activity_names:
                                activity_duration = min(act.get("recommended_duration_min", 60), 90)  # Cap at 90 min
                                travel_time = act.get("travel_time_min", 0) or 0
                                duration = activity_duration + travel_time + 30
                                
                                if duration <= remain:
                                    segments.append({
                                        "type": "activity",
                                        "name": act.get("name", ""),
                                        "address": act.get("address"),
                                        "duration_min": activity_duration,
                                        "travel_time_min": travel_time if travel_time > 0 else None,
                                        "estimated_cost_vnd": act.get("estimated_cost_vnd", 0),
                                        "category": act.get("category"),
                                        "rating": act.get("rating"),
                                        "coordinates": act.get("coordinates"),
                                        "algo_score": act.get("algo_score", 0),
                                    })
                                    day_activity_names.add(normalized_act_name)
                                    remain -= duration
                                    other_count += 1
                                    other_idx += 1
                                    logger.info(f"Day {d + 1}: Added activity before lunch - {act.get('name')}")
            
            lunch, food_idx = get_next_food(day_activity_names, all_used_food_names)
            if lunch:
                food_duration = lunch.get("recommended_duration_min", 75)
                travel_time = lunch.get("travel_time_min", 0) or 0
                duration = food_duration + travel_time + 30
                
                # Ensure lunch is scheduled in 11:30-13:30 time slot
                if duration <= remain:
                    segments.append({
                        "type": "activity",
                        "name": lunch.get("name", ""),
                        "address": lunch.get("address"),
                        "duration_min": food_duration,
                        "travel_time_min": travel_time if travel_time > 0 else None,
                        "estimated_cost_vnd": lunch.get("estimated_cost_vnd", 0),
                        "category": "food",
                        "meal_type": "lunch",
                        "meal_time_slot": "11:30-13:30",  # Stage 4: Strict meal time slot
                        "rating": lunch.get("rating"),
                        "votes": lunch.get("votes", 0),
                        "price_level": lunch.get("price_level"),
                        "coordinates": lunch.get("coordinates"),
                        "algo_score": lunch.get("algo_score", 0),
                        "description": lunch.get("description", ""),
                    })
                    day_activity_names.add(self._normalize_vietnamese_text(lunch.get("name", "")))
                    remain -= duration
                    # food_idx already incremented in get_next_food()
                    logger.info(f"Day {d + 1}: Added lunch (11:30-13:30) - {lunch.get('name')} (food_idx: {food_idx}, total used: {len(all_used_food_names)})")
                else:
                    # Lunch doesn't fit, but we still add it (essential meal)
                    segments.append({
                        "type": "activity",
                        "name": lunch.get("name", ""),
                        "address": lunch.get("address"),
                        "duration_min": min(food_duration, max(30, remain - 30)) if remain > 30 else food_duration,
                        "travel_time_min": travel_time if travel_time > 0 else None,
                        "estimated_cost_vnd": lunch.get("estimated_cost_vnd", 0),
                        "category": "food",
                        "meal_type": "lunch",
                        "meal_time_slot": "11:30-13:30",  # Stage 4: Strict meal time slot
                        "rating": lunch.get("rating"),
                        "votes": lunch.get("votes", 0),
                        "price_level": lunch.get("price_level"),
                        "coordinates": lunch.get("coordinates"),
                        "algo_score": lunch.get("algo_score", 0),
                        "description": lunch.get("description", ""),
                    })
                    day_activity_names.add(self._normalize_vietnamese_text(lunch.get("name", "")))
                    # food_idx already incremented in get_next_food()
                    remain = max(0, remain - min(food_duration, max(30, remain - 30)))
                    logger.info(f"Day {d + 1}: Added lunch (11:30-13:30, capped) - {lunch.get('name')}")

            # 4. Add more other activities if time allows (after lunch)
            # Continue adding activities to ensure minimum per day, especially for later days
            skipped_count_after_lunch = 0
            max_skips_after_lunch = 5  # Limit skips after lunch as well
            while other_idx < len(other_activities) and other_count < max_other_activities_per_day and remain > 30:
                act = other_activities[other_idx]
                act_name = act.get("name", "").strip()
                if not act_name:
                    other_idx += 1
                    continue
                
                normalized_act_name = self._normalize_vietnamese_text(act_name)
                
                # Skip if already added to this day
                if normalized_act_name in day_activity_names:
                    other_idx += 1
                    continue
                
                activity_duration = act.get("recommended_duration_min", 60)
                travel_time = act.get("travel_time_min", 0) or 0
                duration = activity_duration + travel_time + 30

                # For later days, be more lenient to ensure they have activities
                needs_minimum = (other_count < min_activities_per_day) and (d >= total_days - 2)
                
                if duration <= remain or (needs_minimum and remain > 30):
                    # If it doesn't fit but we need minimum, add it with reduced duration
                    actual_duration = min(activity_duration, remain - 30) if duration > remain and needs_minimum else activity_duration
                    
                    segments.append({
                        "type": "activity",
                        "name": act.get("name", ""),
                        "address": act.get("address"),
                        "duration_min": actual_duration if actual_duration > 0 else activity_duration,
                        "travel_time_min": travel_time if travel_time > 0 else None,
                        "estimated_cost_vnd": act.get("estimated_cost_vnd", 0),
                        "category": act.get("category"),
                        "rating": act.get("rating"),
                        "coordinates": act.get("coordinates"),
                        "algo_score": act.get("algo_score", 0),
                    })
                    day_activity_names.add(normalized_act_name)
                    remain -= min(duration, remain) if duration > remain and needs_minimum else duration
                    other_count += 1
                    other_idx += 1
                    skipped_count_after_lunch = 0  # Reset skip counter
                    
                    # If we added with reduced duration, break to preserve remaining time
                    if duration > remain and needs_minimum:
                        logger.info(f"Day {d + 1}: Added activity after lunch with reduced duration - {act.get('name')}")
                        break
                else:
                    skipped_count_after_lunch += 1
                    if skipped_count_after_lunch >= max_skips_after_lunch:
                        # Too many skips, break to preserve remaining activities
                        logger.info(f"Day {d + 1}: Skipped {skipped_count_after_lunch} activities after lunch, preserving remaining for other days")
                        break
                    other_idx += 1
                    if other_idx >= len(other_activities):
                        break

            # 5. Add drink (REQUIRED - at least 1 drink per day)
            drink, drink_idx = get_next_drink(day_activity_names, all_used_drink_names)
            if drink:
                drink_duration = drink.get("recommended_duration_min", 60)
                travel_time = drink.get("travel_time_min", 0) or 0
                duration = drink_duration + travel_time + 30

                # Always add drink (required), even if it exceeds remain
                if duration <= remain:
                    segments.append({
                        "type": "activity",
                        "name": drink.get("name", ""),
                        "address": drink.get("address"),
                        "duration_min": drink_duration,
                        "travel_time_min": travel_time if travel_time > 0 else None,
                        "estimated_cost_vnd": drink.get("estimated_cost_vnd", 0),
                        "category": "drink",
                        "rating": drink.get("rating"),
                        "votes": drink.get("votes", 0),
                        "price_level": drink.get("price_level"),
                        "coordinates": drink.get("coordinates"),
                        "algo_score": drink.get("algo_score", 0),
                        "description": drink.get("description", ""),  # Add description
                    })
                    day_activity_names.add(self._normalize_vietnamese_text(drink.get("name", "")))
                    remain -= duration
                    # drink_idx already incremented in get_next_drink()
                    logger.info(f"Day {d + 1}: Added drink - {drink.get('name')} (drink_idx: {drink_idx}, total used: {len(all_used_drink_names)})")
                else:
                    # Drink doesn't fit, but we still add it (required)
                    segments.append({
                        "type": "activity",
                        "name": drink.get("name", ""),
                        "address": drink.get("address"),
                        "duration_min": min(drink_duration, max(30, remain - 30)) if remain > 30 else drink_duration,
                        "travel_time_min": travel_time if travel_time > 0 else None,
                        "estimated_cost_vnd": drink.get("estimated_cost_vnd", 0),
                        "category": "drink",
                        "rating": drink.get("rating"),
                        "votes": drink.get("votes", 0),
                        "price_level": drink.get("price_level"),
                        "coordinates": drink.get("coordinates"),
                        "algo_score": drink.get("algo_score", 0),
                        "description": drink.get("description", ""),  # Add description
                    })
                    day_activity_names.add(self._normalize_vietnamese_text(drink.get("name", "")))
                    remain = max(0, remain - min(drink_duration, max(30, remain - 30)))
                    # drink_idx already incremented in get_next_drink()
                    logger.info(f"Day {d + 1}: Added drink (capped) - {drink.get('name')} (drink_idx: {drink_idx}, total used: {len(all_used_drink_names)})")
            else:
                logger.warning(f"Day {d + 1}: Could not add drink - no available drink places")

            # 6. Add dinner (18:00-20:00) - ALWAYS add, Stage 4: Meal Scheduling (Strict)
            # CRITICAL: Ensure there's at least 1 activity or drink between lunch and dinner
            # Check if last segment is food (lunch)
            last_segment_is_food = len(segments) > 0 and segments[-1].get("category") == "food"
            if last_segment_is_food:
                # Need to add activity or drink before dinner
                logger.info(f"Day {d + 1}: Last segment is food, adding activity/drink before dinner")
                
                # Try to add a drink first (shorter duration)
                if remain > 60:
                    drink_before_dinner, drink_idx_temp = get_next_drink(day_activity_names, all_used_drink_names)
                    if drink_before_dinner:
                        drink_duration = drink_before_dinner.get("recommended_duration_min", 60)
                        travel_time = drink_before_dinner.get("travel_time_min", 0) or 0
                        duration = drink_duration + travel_time + 30
                        
                        if duration <= remain:
                            segments.append({
                                "type": "activity",
                                "name": drink_before_dinner.get("name", ""),
                                "address": drink_before_dinner.get("address"),
                                "duration_min": drink_duration,
                                "travel_time_min": travel_time if travel_time > 0 else None,
                                "estimated_cost_vnd": drink_before_dinner.get("estimated_cost_vnd", 0),
                                "category": "drink",
                                "rating": drink_before_dinner.get("rating"),
                                "votes": drink_before_dinner.get("votes", 0),
                                "price_level": drink_before_dinner.get("price_level"),
                                "coordinates": drink_before_dinner.get("coordinates"),
                                "algo_score": drink_before_dinner.get("algo_score", 0),
                                "description": drink_before_dinner.get("description", ""),
                            })
                            day_activity_names.add(self._normalize_vietnamese_text(drink_before_dinner.get("name", "")))
                            remain -= duration
                            logger.info(f"Day {d + 1}: Added drink before dinner - {drink_before_dinner.get('name')}")
                
                # If no drink added, try to add a short activity
                # Re-check if last segment is still food (drink might have been added)
                if len(segments) > 0 and segments[-1].get("category") == "food":
                    # Still need activity/drink, try short activity
                    if other_idx < len(other_activities) and remain > 30:
                        act = other_activities[other_idx]
                        act_name = act.get("name", "").strip()
                        if act_name:
                            normalized_act_name = self._normalize_vietnamese_text(act_name)
                            if normalized_act_name not in day_activity_names:
                                activity_duration = min(act.get("recommended_duration_min", 60), 90)  # Cap at 90 min
                                travel_time = act.get("travel_time_min", 0) or 0
                                duration = activity_duration + travel_time + 30
                                
                                if duration <= remain:
                                    segments.append({
                                        "type": "activity",
                                        "name": act.get("name", ""),
                                        "address": act.get("address"),
                                        "duration_min": activity_duration,
                                        "travel_time_min": travel_time if travel_time > 0 else None,
                                        "estimated_cost_vnd": act.get("estimated_cost_vnd", 0),
                                        "category": act.get("category"),
                                        "rating": act.get("rating"),
                                        "coordinates": act.get("coordinates"),
                                        "algo_score": act.get("algo_score", 0),
                                    })
                                    day_activity_names.add(normalized_act_name)
                                    remain -= duration
                                    other_count += 1
                                    other_idx += 1
                                    logger.info(f"Day {d + 1}: Added activity before dinner - {act.get('name')}")
            
            dinner, food_idx = get_next_food(day_activity_names, all_used_food_names)
            if dinner:
                food_duration = dinner.get("recommended_duration_min", 75)
                travel_time = dinner.get("travel_time_min", 0) or 0
                duration = food_duration + travel_time + 30
                
                # Ensure dinner is scheduled in 18:00-20:00 time slot
                # Always add dinner even if it exceeds remain (essential meal)
                segments.append({
                    "type": "activity",
                    "name": dinner.get("name", ""),
                    "address": dinner.get("address"),
                    "duration_min": min(food_duration, max(30, remain - 30)) if remain > 30 else food_duration,
                    "travel_time_min": travel_time if travel_time > 0 else None,
                    "estimated_cost_vnd": dinner.get("estimated_cost_vnd", 0),
                    "category": "food",
                    "meal_type": "dinner",
                    "meal_time_slot": "18:00-20:00",  # Stage 4: Strict meal time slot
                    "rating": dinner.get("rating"),
                    "votes": dinner.get("votes", 0),
                    "price_level": dinner.get("price_level"),
                    "coordinates": dinner.get("coordinates"),
                    "algo_score": dinner.get("algo_score", 0),
                    "description": dinner.get("description", ""),
                })
                day_activity_names.add(self._normalize_vietnamese_text(dinner.get("name", "")))
                # food_idx already incremented in get_next_food()
                logger.info(f"Day {d + 1}: Added dinner (18:00-20:00) - {dinner.get('name')} (food_idx: {food_idx}, total used: {len(all_used_food_names)})")

            # 7. Add optional 2nd drink place if time allows (for 1-2 drink places per day)
            if remain > 60:  # Only add if we have at least 60 minutes left
                drink2, drink_idx = get_next_drink(day_activity_names, all_used_drink_names)
                if drink2:
                    drink_duration = drink2.get("recommended_duration_min", 60)
                    travel_time = drink2.get("travel_time_min", 0) or 0
                    duration = drink_duration + travel_time + 30
                    
                    if duration <= remain:
                        segments.append({
                            "type": "activity",
                            "name": drink2.get("name", ""),
                            "address": drink2.get("address"),
                            "duration_min": drink_duration,
                            "travel_time_min": travel_time if travel_time > 0 else None,
                            "estimated_cost_vnd": drink2.get("estimated_cost_vnd", 0),
                            "category": "drink",
                            "rating": drink2.get("rating"),
                            "votes": drink2.get("votes", 0),
                            "price_level": drink2.get("price_level"),
                            "coordinates": drink2.get("coordinates"),
                            "algo_score": drink2.get("algo_score", 0),
                            "description": drink2.get("description", ""),  # Add description
                        })
                        day_activity_names.add(self._normalize_vietnamese_text(drink2.get("name", "")))
                        remain -= duration
                        # drink_idx already incremented in get_next_drink()
                        logger.info(f"Day {d + 1}: Added 2nd drink - {drink2.get('name')} (drink_idx: {drink_idx}, total used: {len(all_used_drink_names)})")

            # Calculate travel time between consecutive activities in this day
            segments = await self._calculate_travel_times_between_segments(segments, mode="driving")
            
            # Count food and drink in segments
            food_count = sum(1 for seg in segments if seg.get("category") == "food")
            drink_count = sum(1 for seg in segments if seg.get("category") == "drink" or seg.get("category") == "coffee")
            
            # Validate requirements: at least 3 food places (breakfast, lunch, dinner) and 1 drink place per day
            if food_count < 3:
                logger.warning(f"Day {d + 1} ({date}): Only {food_count} food places (required: 3)")
            if drink_count < 1:
                logger.warning(f"Day {d + 1} ({date}): Only {drink_count} drink places (required: 1)")
            
            logger.info(f"Day {d + 1} ({date}): {len(segments)} activities scheduled ({other_count} other activities, {food_count} food, {drink_count} drink)")
            days.append({
                "date": date,
                "hotel": best_hotel,
                "segments": segments
            })

        # ---------------------------------------------------------
        # 5. Save short-term memory + update long-term memory
        # ---------------------------------------------------------
        self.db.set_short_memory(request_id, user_id, {
            "days": days,
            "budgets": budget_alloc
        })

        # Update long-term memory counters
        long = pref_bundle.long_term
        long.activity_preferences = list(set(long.activity_preferences + soft.interests))
        long.trips_planned = long.trips_planned + 1

        self.db.set_long_memory(str(user_id), long.dict())

        # ---------------------------------------------------------
        # 6. Validate and fix meal placement (ensure activities between meals)
        # ---------------------------------------------------------
        days = await self._validate_and_fix_meal_placement(
            days=days,
            all_activities=scored_with_travel,
            energy=soft.energy,
            activity_budget=planner_request.get("activity_budget", 1_000_000),
            city=hard.destination
        )

        # ---------------------------------------------------------
        # 7. Stage 5: Generate Hybrid Logic Compliance Report
        # ---------------------------------------------------------
        compliance_report = self._generate_compliance_report(
            days=days,
            activities=scored_with_travel,
            preferences=soft.interests,
            energy=soft.energy,
            total_days=total_days
        )
        
        logger.info(f"Compliance Report: {compliance_report['final_confidence_score']}/100")

        # ---------------------------------------------------------
        # 8. Build response
        # ---------------------------------------------------------
        return {
            "itinerary_id": request_id,
            "budget_allocation": budget_alloc,
            "hotel": best_hotel,
            "transportation": trans_resp["payload"],
            "activities": scored_with_travel,
            "days": days,
            "compliance_report": compliance_report,  # Stage 5: Compliance Report
        }

    async def _validate_and_fix_meal_placement(
        self,
        days: List[Dict[str, Any]],
        all_activities: List[Dict[str, Any]],
        energy: str,
        activity_budget: float,
        city: str
    ) -> List[Dict[str, Any]]:
        """
        Validate and fix meal placement to ensure there's always at least 1 activity between meals.
        
        Rules:
        - Breakfast → Activity → Lunch → Activity → Dinner
        - Never: Breakfast → Lunch or Lunch → Dinner
        
        Args:
            days: List of day dictionaries with segments
            all_activities: All available activities to choose from
            energy: User energy level (low, medium, high)
            activity_budget: Budget for activities
            city: City name for searching nearby places if needed
        
        Returns:
            Updated days list with activities inserted between consecutive meals
        """
        from app.utils.scoring import score_activity_with_hybrid_algorithm
        from app.models.preference_models import compute_preference_score
        from app.core.llm import gpt_preference_score
        
        logger.info("Validating and fixing meal placement...")
        
        fixed_days = []
        
        for day_idx, day in enumerate(days, 1):
            segments = day.get("segments", [])
            if not segments:
                fixed_days.append(day)
                continue
            
            # Track which activities are already used in this day
            day_activity_names = set()
            for seg in segments:
                if seg.get("type") == "activity":
                    name = seg.get("name", "").strip()
                    if name:
                        day_activity_names.add(self._normalize_vietnamese_text(name))
            
            # Check for consecutive meals and insert activities
            new_segments = []
            i = 0
            
            while i < len(segments):
                current_seg = segments[i]
                new_segments.append(current_seg)
                
                # Check if current segment is a meal
                # A meal can be identified by: meal_type OR category == "food"
                current_meal_type = current_seg.get("meal_type")
                current_is_food = current_seg.get("category") == "food"
                current_is_meal = current_meal_type in ["breakfast", "lunch", "dinner"] or current_is_food
                
                if current_is_meal:
                    # Check if next segment is also a meal (consecutive meals)
                    if i + 1 < len(segments):
                        next_seg = segments[i + 1]
                        next_meal_type = next_seg.get("meal_type")
                        next_is_food = next_seg.get("category") == "food"
                        next_is_meal = next_meal_type in ["breakfast", "lunch", "dinner"] or next_is_food
                        
                        # Check for consecutive meals: breakfast → lunch or lunch → dinner
                        # Also check if both are food (even without meal_type)
                        is_consecutive_meals = False
                        
                        if current_meal_type and next_meal_type:
                            # Both have meal_type - check specific patterns
                            is_consecutive_meals = (
                                (current_meal_type == "breakfast" and next_meal_type == "lunch") or
                                (current_meal_type == "lunch" and next_meal_type == "dinner")
                            )
                        elif current_is_food and next_is_food:
                            # Both are food but may not have meal_type set
                            # Check if they are consecutive in the list (likely consecutive meals)
                            # We need to be more careful here - only flag if we're sure
                            # For now, if both are food and consecutive, treat as consecutive meals
                            is_consecutive_meals = True
                            logger.info(
                                f"Day {day_idx}: Found consecutive food segments (may be meals): "
                                f"'{current_seg.get('name')}' → '{next_seg.get('name')}'"
                            )
                        
                        if is_consecutive_meals:
                            meal_desc = f"{current_meal_type or 'food'}" if current_meal_type else "food"
                            next_meal_desc = f"{next_meal_type or 'food'}" if next_meal_type else "food"
                            logger.warning(
                                f"Day {day_idx}: Found consecutive meals: {meal_desc} → {next_meal_desc}. "
                                f"Inserting activity between them."
                            )
                            
                            # Find best activity to insert between meals
                            best_activity = await self._find_best_activity_between_meals(
                                previous_meal=current_seg,
                                next_meal=next_seg,
                                all_activities=all_activities,
                                day_activity_names=day_activity_names,
                                energy=energy,
                                activity_budget=activity_budget,
                                city=city
                            )
                            
                            if best_activity:
                                # Insert activity between meals
                                activity_segment = {
                                    "type": "activity",
                                    "name": best_activity.get("name", ""),
                                    "address": best_activity.get("address"),
                                    "duration_min": best_activity.get("recommended_duration_min", 60),
                                    "travel_time_min": best_activity.get("travel_time_min", 0) or None,
                                    "estimated_cost_vnd": best_activity.get("estimated_cost_vnd", 0),
                                    "category": best_activity.get("category"),
                                    "rating": best_activity.get("rating"),
                                    "coordinates": best_activity.get("coordinates"),
                                    "algo_score": best_activity.get("algo_score", 0),
                                }
                                new_segments.append(activity_segment)
                                day_activity_names.add(self._normalize_vietnamese_text(best_activity.get("name", "")))
                                meal_desc = f"{current_meal_type or 'food'}" if current_meal_type else "food"
                                next_meal_desc = f"{next_meal_type or 'food'}" if next_meal_type else "food"
                                logger.info(
                                    f"Day {day_idx}: Inserted activity '{best_activity.get('name')}' "
                                    f"between {meal_desc} and {next_meal_desc}"
                                )
                            else:
                                meal_desc = f"{current_meal_type or 'food'}" if current_meal_type else "food"
                                next_meal_desc = f"{next_meal_type or 'food'}" if next_meal_type else "food"
                                logger.warning(
                                    f"Day {day_idx}: Could not find suitable activity to insert between "
                                    f"{meal_desc} and {next_meal_desc}. Meals remain consecutive."
                                )
                
                i += 1
            
            # Recalculate travel times after inserting activities
            if len(new_segments) != len(segments):
                new_segments = await self._calculate_travel_times_between_segments(new_segments, mode="driving")
            
            # Update day with fixed segments
            fixed_day = day.copy()
            fixed_day["segments"] = new_segments
            fixed_days.append(fixed_day)
            
            # Final validation: check if there are still consecutive meals
            for j in range(len(new_segments) - 1):
                current_seg = new_segments[j]
                next_seg = new_segments[j + 1]
                
                # Check if both are meals (by meal_type or category)
                current_meal_type = current_seg.get("meal_type")
                current_is_food = current_seg.get("category") == "food"
                current_is_meal = current_meal_type in ["breakfast", "lunch", "dinner"] or current_is_food
                
                next_meal_type = next_seg.get("meal_type")
                next_is_food = next_seg.get("category") == "food"
                next_is_meal = next_meal_type in ["breakfast", "lunch", "dinner"] or next_is_food
                
                if current_is_meal and next_is_meal:
                    # Both are meals - check if they're consecutive
                    if current_meal_type and next_meal_type:
                        # Both have meal_type
                        if (current_meal_type == "breakfast" and next_meal_type == "lunch") or \
                           (current_meal_type == "lunch" and next_meal_type == "dinner"):
                            logger.error(
                                f"Day {day_idx}: VALIDATION FAILED - Still has consecutive meals: "
                                f"{current_meal_type} → {next_meal_type} "
                                f"('{current_seg.get('name')}' → '{next_seg.get('name')}')"
                            )
                    elif current_is_food and next_is_food:
                        # Both are food but may not have meal_type - still flag as potential issue
                        logger.warning(
                            f"Day {day_idx}: VALIDATION WARNING - Found consecutive food segments: "
                            f"'{current_seg.get('name')}' → '{next_seg.get('name')}' "
                            f"(may be consecutive meals without meal_type set)"
                        )
        
        logger.info("Meal placement validation and fixing completed")
        return fixed_days
    
    async def _find_best_activity_between_meals(
        self,
        previous_meal: Dict[str, Any],
        next_meal: Dict[str, Any],
        all_activities: List[Dict[str, Any]],
        day_activity_names: set,
        energy: str,
        activity_budget: float,
        city: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best activity to insert between two consecutive meals.
        
        Criteria:
        - Travel time ≤ 30 minutes from previous meal
        - Duration fits user energy level
        - Not already used in this day
        - Highest hybrid score
        
        Args:
            previous_meal: The meal before (breakfast or lunch)
            next_meal: The meal after (lunch or dinner)
            all_activities: All available activities
            day_activity_names: Set of normalized activity names already used in this day
            energy: User energy level
            activity_budget: Budget for activities
            city: City name for fallback search
        
        Returns:
            Best activity dict or None if none found
        """
        from app.utils.scoring import score_activity_with_hybrid_algorithm
        from app.models.preference_models import compute_preference_score
        from app.core.llm import gpt_preference_score
        
        previous_coords = previous_meal.get("coordinates")
        if not previous_coords or not previous_coords.get("lat") or not previous_coords.get("lng"):
            logger.warning("Previous meal has no coordinates, cannot calculate travel time")
            # Still try to find activity without travel time constraint
            previous_coords = None
        
        # Filter activities: exclude food/drink, not already used, has coordinates
        candidate_activities = []
        for act in all_activities:
            # Skip food and drink (we need real attractions)
            category = act.get("category", "")
            if category in ["food", "drink", "coffee"]:
                continue
            
            # Skip if already used in this day
            name = act.get("name", "").strip()
            if not name:
                continue
            normalized_name = self._normalize_vietnamese_text(name)
            if normalized_name in day_activity_names:
                continue
            
            # Prefer activities with coordinates
            coords = act.get("coordinates")
            if not coords or not coords.get("lat") or not coords.get("lng"):
                continue
            
            candidate_activities.append(act)
        
        if not candidate_activities:
            logger.warning("No candidate activities found. Trying fallback search...")
            # Fallback: search for nearby attractions
            if previous_coords:
                fallback_activities = await self._search_nearby_attractions(
                    location=previous_coords,
                    city=city,
                    radius_meters=5000,  # 5km radius
                    exclude_names=day_activity_names
                )
                candidate_activities.extend(fallback_activities)
        
        if not candidate_activities:
            logger.error("No activities available to insert between meals")
            return None
        
        # Calculate travel time and score for each candidate
        scored_candidates = []
        
        for act in candidate_activities:
            travel_time_min = 0
            
            # Calculate travel time from previous meal if coordinates available
            if previous_coords:
                act_coords = act.get("coordinates")
                if act_coords and act_coords.get("lat") and act_coords.get("lng"):
                    try:
                        results = self.maps_service.get_distance_matrix(
                            origins=[previous_coords],
                            destinations=[act_coords],
                            mode="driving"
                        )
                        if results and len(results) > 0:
                            travel_time_seconds = results[0].get("travelTime", 0)
                            travel_time_min = travel_time_seconds // 60
                    except Exception as e:
                        logger.warning(f"Error calculating travel time: {e}")
                        travel_time_min = 999  # Penalize if we can't calculate
            
            # Filter: travel time must be ≤ 30 minutes
            if travel_time_min > 30:
                continue
            
            # Check duration fit for energy level
            duration_min = act.get("recommended_duration_min", act.get("duration_min", 60))
            if energy == "low" and duration_min > 120:  # Low energy: prefer shorter activities
                continue
            
            # Calculate hybrid score with travel time
            pref_score_components = act.get("pref_score_components", {})
            user_fit = pref_score_components.get("final_score", act.get("gpt_pref_score", 0.5))
            
            algo_score = score_activity_with_hybrid_algorithm(
                place=act,
                preference_score=user_fit,
                energy=energy,
                activity_budget=activity_budget,
                travel_time_min=travel_time_min
            )
            
            scored_candidates.append({
                "activity": act,
                "travel_time_min": travel_time_min,
                "score": algo_score
            })
        
        if not scored_candidates:
            logger.warning("No activities meet travel time constraint (≤30min). Trying expanded search...")
            # Expand search: allow up to 45 minutes travel time
            for act in candidate_activities:
                travel_time_min = 0
                if previous_coords:
                    act_coords = act.get("coordinates")
                    if act_coords and act_coords.get("lat") and act_coords.get("lng"):
                        try:
                            results = self.maps_service.get_distance_matrix(
                                origins=[previous_coords],
                                destinations=[act_coords],
                                mode="driving"
                            )
                            if results and len(results) > 0:
                                travel_time_seconds = results[0].get("travelTime", 0)
                                travel_time_min = travel_time_seconds // 60
                        except Exception as e:
                            travel_time_min = 999
                
                if travel_time_min > 45:  # Expanded limit
                    continue
                
                duration_min = act.get("recommended_duration_min", act.get("duration_min", 60))
                if energy == "low" and duration_min > 120:
                    continue
                
                pref_score_components = act.get("pref_score_components", {})
                user_fit = pref_score_components.get("final_score", act.get("gpt_pref_score", 0.5))
                
                algo_score = score_activity_with_hybrid_algorithm(
                    place=act,
                    preference_score=user_fit,
                    energy=energy,
                    activity_budget=activity_budget,
                    travel_time_min=travel_time_min
                )
                
                scored_candidates.append({
                    "activity": act,
                    "travel_time_min": travel_time_min,
                    "score": algo_score
                })
        
        if not scored_candidates:
            logger.error("No suitable activities found even with expanded search")
            return None
        
        # Sort by score (highest first) and return best
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        best = scored_candidates[0]
        
        # Update activity with travel time
        best_activity = best["activity"].copy()
        best_activity["travel_time_min"] = best["travel_time_min"]
        
        logger.info(
            f"Selected activity '{best_activity.get('name')}' "
            f"(score: {best['score']:.4f}, travel: {best['travel_time_min']}min)"
        )
        
        return best_activity
    
    async def _search_nearby_attractions(
        self,
        location: Dict[str, float],
        city: str,
        radius_meters: int = 5000,
        exclude_names: set = None
    ) -> List[Dict[str, Any]]:
        """
        Search for nearby attractions as fallback when no activities available.
        
        Args:
            location: {"lat": float, "lng": float}
            city: City name
            radius_meters: Search radius in meters
            exclude_names: Set of normalized names to exclude
        
        Returns:
            List of activity dictionaries
        """
        if exclude_names is None:
            exclude_names = set()
        
        try:
            # Search for tourist attractions near the location
            query = f"điểm tham quan {city}"
            places = self.maps_service.search_places(
                query=query,
                location=location,
                limit=20
            )
            
            # Convert to activity format
            activities = []
            for place in places:
                name = place.get("displayName", {}).get("text", "").strip()
                if not name:
                    continue
                
                normalized_name = self._normalize_vietnamese_text(name)
                if normalized_name in exclude_names:
                    continue
                
                # Skip irrelevant places (companies, offices, service providers)
                types = place.get("types", [])
                if self.place_service._is_irrelevant_place(name, types):
                    continue
                
                # Skip if it's a restaurant, cafe, or coffee shop (coffee = break, not real attraction)
                if any(t in ["restaurant", "cafe", "coffee_shop", "food", "meal_takeaway"] for t in types):
                    continue
                
                # Extract coordinates
                location_data = place.get("location", {})
                if not location_data:
                    continue
                
                coords = {
                    "lat": location_data.get("latitude"),
                    "lng": location_data.get("longitude")
                }
                
                if not coords.get("lat") or not coords.get("lng"):
                    continue
                
                # Calculate travel time from location
                travel_time_min = 0
                try:
                    results = self.maps_service.get_distance_matrix(
                        origins=[location],
                        destinations=[coords],
                        mode="driving"
                    )
                    if results and len(results) > 0:
                        travel_time_seconds = results[0].get("travelTime", 0)
                        travel_time_min = travel_time_seconds // 60
                except:
                    pass
                
                activity = {
                    "name": name,
                    "address": place.get("formattedAddress", ""),
                    "rating": place.get("rating", 0),
                    "votes": place.get("userRatingCount", 0),
                    "coordinates": coords,
                    "category": "culture",  # Default category
                    "duration_min": 60,  # Default duration
                    "recommended_duration_min": 60,
                    "estimated_cost_vnd": 0,
                    "travel_time_min": travel_time_min,
                    "algo_score": 0.5,  # Default score
                    "gpt_pref_score": 0.5,
                    "pref_score_components": {"final_score": 0.5}
                }
                
                activities.append(activity)
            
            logger.info(f"Found {len(activities)} nearby attractions as fallback")
            return activities
            
        except Exception as e:
            logger.error(f"Error searching nearby attractions: {e}")
            return []

    def _generate_compliance_report(
        self,
        days: List[Dict[str, Any]],
        activities: List[Dict[str, Any]],
        preferences: List[str],
        energy: str,
        total_days: int
    ) -> Dict[str, Any]:
        """
        Stage 5: Validation Checklist Output - Hybrid Logic Compliance Report
        
        Returns compliance status for:
        - Preference filtering
        - Hybrid scoring (all terms)
        - TravelTime Matrix
        - Energy-aware planning
        - 3 meals/day
        - Duplicate avoidance
        """
        report = {
            "preference_filtering": "PASS",
            "hybrid_scoring": "PASS",
            "travel_time_matrix": "PASS",
            "energy_aware_planning": "PASS",
            "three_meals_per_day": "PASS",
            "duplicate_avoidance": "PASS",
            "missing_items": [],
            "fix_suggestions": [],
            "final_confidence_score": 100
        }
        
        # 1. Check Preference Filtering
        if preferences:
            # Check if activities match preferences
            matched_count = 0
            for act in activities[:20]:  # Check top 20
                act_name = act.get("name", "").lower()
                for pref in preferences:
                    if pref.lower() in act_name:
                        matched_count += 1
                        break
            
            match_ratio = matched_count / min(20, len(activities)) if activities else 0
            if match_ratio >= 0.5:
                report["preference_filtering"] = "PASS"
            elif match_ratio >= 0.3:
                report["preference_filtering"] = "PARTIAL"
                report["missing_items"].append(f"Only {match_ratio*100:.0f}% preference match")
            else:
                report["preference_filtering"] = "FAIL"
                report["missing_items"].append("Low preference match ratio")
                report["fix_suggestions"].append("Expand search radius or add fallback categories")
        else:
            report["preference_filtering"] = "PARTIAL"
            report["missing_items"].append("No preferences provided")
        
        # 2. Check Hybrid Scoring (all terms present)
        hybrid_scoring_ok = True
        for act in activities[:10]:  # Check top 10
            if "algo_score" not in act:
                hybrid_scoring_ok = False
                break
            # Check if rating, votes, preference_score, duration, travel_time, cost are used
            if not act.get("rating") or not act.get("votes"):
                hybrid_scoring_ok = False
                break
        
        if not hybrid_scoring_ok:
            report["hybrid_scoring"] = "PARTIAL"
            report["missing_items"].append("Some activities missing scoring components")
            report["fix_suggestions"].append("Ensure all POIs have rating, votes, and algo_score")
        else:
            report["hybrid_scoring"] = "PASS"
        
        # 3. Check TravelTime Matrix (API usage)
        travel_time_used = 0
        for act in activities[:20]:
            if act.get("travel_time_min", 0) > 0:
                travel_time_used += 1
        
        travel_time_ratio = travel_time_used / min(20, len(activities)) if activities else 0
        if travel_time_ratio >= 0.5:
            report["travel_time_matrix"] = "PASS"
        elif travel_time_ratio >= 0.3:
            report["travel_time_matrix"] = "PARTIAL"
            report["missing_items"].append(f"Only {travel_time_ratio*100:.0f}% activities have travel time")
        else:
            report["travel_time_matrix"] = "FAIL"
            report["missing_items"].append("Travel time not calculated for most activities")
            report["fix_suggestions"].append("Ensure Distance Matrix API is called for all activities")
        
        # 4. Check Energy-aware Planning
        expected_activities_per_day = {
            "low": 2,
            "medium": 3,
            "high": 4
        }
        expected = expected_activities_per_day.get(energy, 3)
        
        energy_ok = True
        for day in days:
            segments = day.get("segments", [])
            other_activities = [s for s in segments if s.get("category") not in ["food", "drink"]]
            if len(other_activities) < expected - 1:  # Allow 1 less for flexibility
                energy_ok = False
                break
        
        if energy_ok:
            report["energy_aware_planning"] = "PASS"
        else:
            report["energy_aware_planning"] = "PARTIAL"
            report["missing_items"].append(f"Some days have fewer than {expected} activities for {energy} energy")
            report["fix_suggestions"].append(f"Adjust activity count to match {energy} energy level")
        
        # 5. Check 3 meals per day
        meals_ok = True
        for day in days:
            segments = day.get("segments", [])
            food_segments = [s for s in segments if s.get("category") == "food"]
            meal_types = [s.get("meal_type") for s in food_segments]
            
            has_breakfast = "breakfast" in meal_types
            has_lunch = "lunch" in meal_types
            has_dinner = "dinner" in meal_types
            
            if not (has_breakfast and has_lunch and has_dinner):
                meals_ok = False
                day_date = day.get("date", "unknown")
                missing = []
                if not has_breakfast:
                    missing.append("breakfast")
                if not has_lunch:
                    missing.append("lunch")
                if not has_dinner:
                    missing.append("dinner")
                report["missing_items"].append(f"Day {day_date}: Missing {', '.join(missing)}")
        
        if meals_ok:
            report["three_meals_per_day"] = "PASS"
        else:
            report["three_meals_per_day"] = "FAIL"
            report["fix_suggestions"].append("Ensure each day has breakfast (07:00-09:00), lunch (11:30-13:30), and dinner (18:00-20:00)")
        
        # 6. Check Duplicate Avoidance
        all_place_names = set()
        duplicates_found = False
        
        for day in days:
            segments = day.get("segments", [])
            for seg in segments:
                name = seg.get("name", "")
                if name:
                    normalized = self._normalize_vietnamese_text(name)
                    if normalized in all_place_names:
                        duplicates_found = True
                        report["missing_items"].append(f"Duplicate found: {name}")
                    all_place_names.add(normalized)
        
        if duplicates_found:
            report["duplicate_avoidance"] = "FAIL"
            report["fix_suggestions"].append("Use normalize_name() for all POIs and check against used set")
        else:
            report["duplicate_avoidance"] = "PASS"
        
        # Calculate final confidence score
        pass_count = sum(1 for key in ["preference_filtering", "hybrid_scoring", "travel_time_matrix", 
                                      "energy_aware_planning", "three_meals_per_day", "duplicate_avoidance"]
                        if report[key] == "PASS")
        partial_count = sum(1 for key in ["preference_filtering", "hybrid_scoring", "travel_time_matrix",
                                         "energy_aware_planning", "three_meals_per_day", "duplicate_avoidance"]
                           if report[key] == "PARTIAL")
        
        # Score: PASS = 100%, PARTIAL = 50%, FAIL = 0%
        score = (pass_count * 100 + partial_count * 50) / 6
        report["final_confidence_score"] = int(score)
        
        return report

    # -----------------------------------------------------------
    # Add activities to existing itinerary (modification)
    # -----------------------------------------------------------
    async def add_activities_to_itinerary(
        self, 
        previous_itinerary: dict, 
        planner_request: dict,
        modification_request: str
    ) -> dict:
        """
        Add new activities to an existing itinerary based on modification request.
        Keeps all existing activities, hotel, transportation, and budget allocation.
        Only fetches and adds new activities matching the modification request.
        
        Args:
            previous_itinerary: The existing itinerary (from database, frontend format)
            planner_request: New planner request with updated constraints
            modification_request: User's modification request text
            
        Returns:
            Updated itinerary with new activities added
        """
        request_id = str(uuid4())
        user_id = planner_request["user_id"]
        planner_request["request_id"] = request_id

        # 1. Build merged preference object
        pref_bundle = self._build_preference_bundle(planner_request, user_id)
        planner_request["preference_bundle"] = pref_bundle

        hard = pref_bundle.hard
        soft = pref_bundle.soft

        # Calculate budget allocation (same as in plan method)
        total_budget = hard.budget_vnd or 5_000_000
        if soft.spending_style == "budget":
            hotel_ratio, activity_ratio, food_ratio = 0.30, 0.10, 0.15
        elif soft.spending_style == "premium":
            hotel_ratio, activity_ratio, food_ratio = 0.50, 0.30, 0.20
        else:
            hotel_ratio, activity_ratio, food_ratio = 0.40, 0.20, 0.15

        budget_alloc = {
            "hotel": round(total_budget * hotel_ratio),
            "activities": round(total_budget * activity_ratio),
            "food": round(total_budget * food_ratio),
            "transport": round(total_budget * (1 - hotel_ratio - activity_ratio - food_ratio)),
        }

        # Get existing itinerary data
        # previous_itinerary is in frontend format, need to convert back to planner format
        existing_days = previous_itinerary.get("days", [])
        existing_hotel = previous_itinerary.get("hotel")
        
        # Extract existing activity names to avoid duplicates
        existing_activity_names = set()
        for day in existing_days:
            for activity in day.get("activities", []):
                existing_activity_names.add(activity.get("name", "").lower())

        logger.info(f"Adding activities to existing itinerary. Existing activities: {len(existing_activity_names)}")

        # Check if this is a replace request (e.g., "đổi địa điểm X thành Y")
        is_replace_request, old_place_name, new_activity_type = self._detect_replace_request(modification_request)
        
        if is_replace_request:
            logger.info(f"Replace request detected: replacing '{old_place_name}' with '{new_activity_type}'")
            # Find and replace the specific place
            return await self._replace_activity_in_itinerary(
                previous_itinerary=previous_itinerary,
                old_place_name=old_place_name,
                new_activity_type=new_activity_type,
                planner_request=planner_request,
                budget_alloc=budget_alloc,
                existing_hotel=existing_hotel,
                request_id=request_id
            )

        # 2. Extract specific activity type from modification request and search for it
        # Instead of fetching all activities, search specifically for what user requested
        city = hard.destination
        activity_type = self._extract_activity_type_from_request(modification_request)
        
        if activity_type:
            logger.info(f"Partial modification detected: searching specifically for '{activity_type}' in {city}")
            # Search specifically for this activity type
            new_ranked_activities = await self._search_specific_activity_type(
                activity_type=activity_type,
                city=city,
                existing_activity_names=existing_activity_names,
                soft_constraints=soft
            )
        else:
            # Fallback: use activities agent but with modification request context
            logger.info("No specific activity type detected, using activities agent with modification context")
            activities_resp = await self.activities_agent.handle(planner_request)
            new_ranked_activities = activities_resp["payload"]["ranked"]
        
        # Filter out activities that already exist
        filtered_new_activities = []
        for act in new_ranked_activities:
            act_name = act.get("name", "").lower()
            if act_name not in existing_activity_names:
                filtered_new_activities.append(act)
        
        logger.info(f"Fetched {len(new_ranked_activities)} new activities, {len(filtered_new_activities)} are new (not duplicates)")

        if not filtered_new_activities:
            logger.warning("No new activities to add after filtering duplicates")
            # Return previous itinerary in planner format (unchanged, just converted)
            planner_days_unchanged = []
            for day_data in existing_days:
                segments = []
                for activity in day_data.get("activities", []):
                    segments.append({
                        "type": "activity",
                        "name": activity.get("name", ""),
                        "address": activity.get("address"),
                        "duration_min": self._parse_duration_to_minutes(activity.get("duration", "60 phút")),
                        "travel_time_min": self._parse_travel_time_to_minutes(activity.get("travelTime")),
                        "estimated_cost_vnd": self._parse_cost_to_vnd(activity.get("cost")),
                        "category": activity.get("icon", "culture"),
                        "rating": activity.get("rating"),
                        "coordinates": None,
                    })
                planner_days_unchanged.append({
                    "date": day_data.get("date", ""),
                    "hotel": existing_hotel,
                    "segments": segments
                })
            
            return {
                "itinerary_id": previous_itinerary.get("itinerary_id", request_id),
                "budget_allocation": budget_alloc,
                "hotel": existing_hotel,
                "transportation": [],
                "activities": [],
                "days": planner_days_unchanged,
            }

        # 3. Calculate travel times for new activities from hotel
        scored_with_travel = []
        if existing_hotel and existing_hotel.get("coordinates"):
            # Get hotel coordinates (handle both formats)
            hotel_coords = existing_hotel.get("coordinates")
            if isinstance(hotel_coords, dict):
                hotel_coords_dict = hotel_coords
            else:
                hotel_coords_dict = {"lat": None, "lng": None}

            activities_with_coords = []
            activities_without_coords = []
            
            for act in filtered_new_activities[:10]:  # Top 10 for travel time calculation
                if act.get("coordinates") and act["coordinates"].get("lat") and act["coordinates"].get("lng"):
                    activities_with_coords.append(act)
                else:
                    act["travel_time_min"] = 0
                    activities_without_coords.append(act)
            
            if activities_with_coords and hotel_coords_dict.get("lat") and hotel_coords_dict.get("lng"):
                legs = []
                for act in activities_with_coords:
                    legs.append({
                        "origin": hotel_coords_dict,
                        "dest": act["coordinates"],
                        "mode": "driving"
                    })

                directions = await self.map_agent.handle({
                    "request_id": request_id,
                    "params": {"legs": legs}
                })

                legs_info = directions["payload"]["legs"]

                for act, leg in zip(activities_with_coords, legs_info):
                    act["travel_time_min"] = leg["duration_min"]
                    act["algo_score"] -= leg["duration_min"] * 0.001
                    scored_with_travel.append(act)
            
            scored_with_travel.extend(activities_without_coords)
            
            # Add remaining activities without travel time
            for act in filtered_new_activities[10:]:
                act["travel_time_min"] = 0
                scored_with_travel.append(act)
        else:
            for act in filtered_new_activities:
                act["travel_time_min"] = 0
            scored_with_travel = filtered_new_activities

        # 4. Merge new activities into existing days
        # Convert frontend format days back to planner format for easier manipulation
        planner_days = []
        for day_data in existing_days:
            segments = []
            for activity in day_data.get("activities", []):
                # Convert frontend activity back to planner segment format
                segments.append({
                    "type": "activity",
                    "name": activity.get("name", ""),
                    "address": activity.get("address"),
                    "duration_min": self._parse_duration_to_minutes(activity.get("duration", "60 phút")),
                    "travel_time_min": self._parse_travel_time_to_minutes(activity.get("travelTime")),
                    "estimated_cost_vnd": self._parse_cost_to_vnd(activity.get("cost")),
                    "category": activity.get("icon", "culture"),
                    "rating": activity.get("rating"),
                    "coordinates": None,  # May not have coordinates in frontend format
                })
            planner_days.append({
                "date": day_data.get("date", ""),
                "hotel": existing_hotel,
                "segments": segments
            })

        # Parse specific days from modification request
        # Handles patterns like: "ngày 2", "ngày thứ 2", "tối ngày 2", "đêm ngày 2", "vào ngày 2", "ngày 3,4", "ngày thứ 2 và 3"
        target_days = None
        message_lower = modification_request.lower()
        
        # Pattern 1: "ngày 2", "ngày 3,4", "vào ngày 2,3"
        specific_days_match = re.search(r'(?:vào\s+)?ngày\s+(\d+(?:\s*[,và]\s*\d+)*)', message_lower)
        if specific_days_match:
            days_str = specific_days_match.group(1)
            # Extract day numbers (e.g., "3,4" -> [3, 4] or "2 và 3" -> [2, 3])
            day_numbers = re.findall(r'\d+', days_str)
            if day_numbers:
                target_days = [int(d) - 1 for d in day_numbers]  # Convert to 0-based index
                logger.info(f"Detected specific days request (pattern 1): adding activities to days {[d+1 for d in target_days]}")
        
        # Pattern 1.5: "tối ngày 2", "đêm ngày 2", "vào tối ngày 2", "vào đêm ngày 2"
        if target_days is None:
            tối_đêm_pattern = re.search(r'(?:vào\s+)?(?:tối|đêm)\s+ngày\s+(\d+)', message_lower)
            if tối_đêm_pattern:
                day_num = int(tối_đêm_pattern.group(1))
                target_days = [day_num - 1]  # Convert to 0-based index
                logger.info(f"Detected specific days request (pattern 1.5 - tối/đêm): adding activities to day {day_num}")
        
        # Pattern 2: "ngày thứ 2", "ngày thứ hai", "vào ngày thứ 2"
        if target_days is None:
            # Map Vietnamese day names to numbers
            day_name_map = {
                "nhất": 1, "một": 1, "1": 1,
                "hai": 2, "2": 2,
                "ba": 3, "3": 3,
                "bốn": 4, "tư": 4, "4": 4,
                "năm": 5, "5": 5,
                "sáu": 6, "6": 6,
                "bảy": 7, "7": 7,
                "tám": 8, "8": 8,
                "chín": 9, "9": 9,
                "mười": 10, "10": 10,
            }
            
            # Try pattern: "ngày thứ X" or "vào ngày thứ X"
            thứ_pattern = re.search(r'(?:vào\s+)?ngày\s+thứ\s+(\d+|nhất|hai|ba|bốn|tư|năm|sáu|bảy|tám|chín|mười|một)', message_lower)
            if thứ_pattern:
                day_str = thứ_pattern.group(1).lower()
                day_num = day_name_map.get(day_str)
                if day_num:
                    target_days = [day_num - 1]  # Convert to 0-based index
                    logger.info(f"Detected specific days request (pattern 2): adding activities to day {day_num}")
            
            # Also try pattern with comma: "ngày thứ 2, 3" or "ngày thứ 2 và 3"
            if target_days is None:
                thứ_multiple_pattern = re.search(r'(?:vào\s+)?ngày\s+thứ\s+(\d+(?:\s*[,và]\s*\d+)*)', message_lower)
                if thứ_multiple_pattern:
                    days_str = thứ_multiple_pattern.group(1)
                    day_numbers = re.findall(r'\d+', days_str)
                    if day_numbers:
                        target_days = [int(d) - 1 for d in day_numbers]
                        logger.info(f"Detected specific days request (pattern 2 multiple): adding activities to days {[d+1 for d in target_days]}")
        
        # Pattern 2.5: "tối ngày thứ 2", "đêm ngày thứ 2"
        if target_days is None:
            tối_đêm_thứ_pattern = re.search(r'(?:vào\s+)?(?:tối|đêm)\s+ngày\s+thứ\s+(\d+)', message_lower)
            if tối_đêm_thứ_pattern:
                day_num = int(tối_đêm_thứ_pattern.group(1))
                target_days = [day_num - 1]
                logger.info(f"Detected specific days request (pattern 2.5 - tối/đêm thứ): adding activities to day {day_num}")
        
        # Add new activities to days, distributing them evenly or to specific days
        if soft.energy == "low":
            daily_minutes = 4 * 60
        elif soft.energy == "high":
            daily_minutes = 9 * 60
        else:
            daily_minutes = 6 * 60

        logger.info(f"Target days: {target_days}, Activities to add: {len(scored_with_travel)}, Daily minutes budget: {daily_minutes}")

        new_act_idx = 0
        for day_idx, day in enumerate(planner_days):
            # Skip days that are not in target_days if specific days were requested
            if target_days is not None and day_idx not in target_days:
                logger.debug(f"Skipping day {day_idx+1} (not in target_days: {target_days})")
                continue
            
            logger.info(f"Processing day {day_idx+1} for adding activities")
            
            # Calculate remaining time in this day
            current_time_used = sum(
                seg.get("duration_min", 60) + (seg.get("travel_time_min", 0) or 0) + 30
                for seg in day["segments"]
            )
            remain = daily_minutes - current_time_used
            logger.info(f"Day {day_idx+1}: current_time_used={current_time_used} minutes, remain={remain} minutes")

            # Add new activities that fit
            # If specific day was requested and we have activities, add at least one even if tight on time
            activities_added_this_day = 0
            while new_act_idx < len(scored_with_travel):
                act = scored_with_travel[new_act_idx]
                activity_duration = act.get("recommended_duration_min", 60)
                travel_time = act.get("travel_time_min", 0) or 0
                duration = activity_duration + travel_time + 30

                # If specific day requested, add at least one activity even if it exceeds remaining time slightly
                # Otherwise, only add if it fits within remaining time
                if target_days is not None and day_idx in target_days:
                    # For specific day requests, be more lenient - add if duration <= remain + 60 (1 hour buffer)
                    can_add = duration <= (remain + 60) or activities_added_this_day == 0
                else:
                    can_add = duration <= remain

                if can_add:
                    day["segments"].append({
                        "type": "activity",
                        "name": act.get("name", ""),
                        "address": act.get("address"),
                        "duration_min": activity_duration,
                        "travel_time_min": travel_time if travel_time > 0 else None,
                        "estimated_cost_vnd": act.get("estimated_cost_vnd", 0),
                        "category": act.get("category"),
                        "rating": act.get("rating"),
                        "coordinates": act.get("coordinates"),
                        "algo_score": act.get("algo_score", 0),
                    })
                    remain -= duration
                    new_act_idx += 1
                    activities_added_this_day += 1
                    logger.info(f"Added activity '{act.get('name')}' to day {day_idx+1}, duration={duration} min, remaining={remain} min")
                    
                    # If specific day requested, add at least one and then check if we should continue
                    if target_days is not None and day_idx in target_days and activities_added_this_day >= 1:
                        # For specific day, add 1-2 activities max
                        if activities_added_this_day >= 2 or remain < 60:
                            break
                else:
                    # Activity doesn't fit, try next one
                    logger.debug(f"Activity '{act.get('name')}' doesn't fit (duration={duration} min, remain={remain} min)")
                    new_act_idx += 1
                    # If we've tried all activities, break
                    if new_act_idx >= len(scored_with_travel):
                        break
                    continue
            
            if activities_added_this_day > 0:
                logger.info(f"Added {activities_added_this_day} activities to day {day_idx+1}")

        logger.info(f"Added {new_act_idx} new activities to existing itinerary")

        # 5. Combine all activities for response
        all_activities = []
        for day in planner_days:
            for seg in day["segments"]:
                if seg["type"] == "activity":
                    all_activities.append({
                        "name": seg["name"],
                        "address": seg.get("address"),
                        "duration_min": seg.get("duration_min", 60),
                        "travel_time_min": seg.get("travel_time_min", 0),
                        "estimated_cost_vnd": seg.get("estimated_cost_vnd", 0),
                        "category": seg.get("category"),
                        "rating": seg.get("rating"),
                        "coordinates": seg.get("coordinates"),
                    })

        # 6. Build response (in planner format)
        return {
            "itinerary_id": previous_itinerary.get("itinerary_id", request_id),
            "budget_allocation": budget_alloc,
            "hotel": existing_hotel,
            "transportation": [],
            "activities": all_activities,
            "days": planner_days,
        }

    def _parse_duration_to_minutes(self, duration_str: str) -> int:
        """Parse duration string like '2 giờ 30 phút' or '60 phút' to minutes"""
        if not duration_str:
            return 60
        try:
            # Simple parsing - can be improved
            if "giờ" in duration_str:
                parts = duration_str.split("giờ")
                hours = int(parts[0].strip()) if parts[0].strip().isdigit() else 0
                minutes = 0
                if len(parts) > 1 and "phút" in parts[1]:
                    minutes = int(parts[1].replace("phút", "").strip()) if parts[1].replace("phút", "").strip().isdigit() else 0
                return hours * 60 + minutes
            elif "phút" in duration_str:
                return int(duration_str.replace("phút", "").strip()) if duration_str.replace("phút", "").strip().isdigit() else 60
            return 60
        except:
            return 60

    def _parse_travel_time_to_minutes(self, travel_time_str: str) -> int:
        """Parse travel time string like '15 phút' or '1h30m' to minutes"""
        if not travel_time_str:
            return 0
        try:
            if "h" in travel_time_str and "m" in travel_time_str:
                # Format: "1h30m"
                parts = travel_time_str.split("h")
                hours = int(parts[0]) if parts[0].isdigit() else 0
                minutes = int(parts[1].replace("m", "")) if parts[1].replace("m", "").isdigit() else 0
                return hours * 60 + minutes
            elif "phút" in travel_time_str:
                return int(travel_time_str.replace("phút", "").strip()) if travel_time_str.replace("phút", "").strip().isdigit() else 0
            return 0
        except:
            return 0

    def _parse_cost_to_vnd(self, cost_str: str) -> int:
        """Parse cost string like '500.000 VNĐ' or '1 triệu VNĐ' to VND"""
        if not cost_str:
            return 0
        try:
            cost_str = cost_str.replace("VNĐ", "").replace(".", "").replace(",", "").strip()
            if "triệu" in cost_str:
                return int(float(cost_str.replace("triệu", "").strip()) * 1000000)
            elif "k" in cost_str.lower():
                return int(float(cost_str.replace("k", "").replace("K", "").strip()) * 1000)
            else:
                return int(float(cost_str)) if cost_str.replace(".", "").isdigit() else 0
        except:
            return 0

    def _detect_replace_request(self, modification_request: str) -> tuple:
        """
        Detect if user wants to replace a specific place in the itinerary.
        Examples: 
        - "đổi địa điểm TuArt wedding thành địa điểm tham quan khác" -> (True, "TuArt wedding", "điểm tham quan")
        - "thay thế X thành Y" -> (True, "X", "Y")
        
        Returns:
            (is_replace, old_place_name, new_activity_type)
        """
        import re
        message_lower = modification_request.lower()
        
        # Patterns for replace requests
        replace_patterns = [
            r"đổi\s+địa\s+điểm\s+(.+?)\s+thành\s+(.+?)(?:\s+khác|$)",
            r"thay\s+thế\s+(.+?)\s+thành\s+(.+?)(?:\s+khác|$)",
            r"đổi\s+(.+?)\s+thành\s+địa\s+điểm\s+(.+?)(?:\s+khác|$)",
            r"thay\s+(.+?)\s+bằng\s+(.+?)(?:\s+khác|$)",
        ]
        
        for pattern in replace_patterns:
            match = re.search(pattern, message_lower)
            if match:
                old_place = match.group(1).strip()
                new_type = match.group(2).strip()
                
                # Extract activity type from new_type
                activity_type = None
                if "điểm tham quan" in new_type or "attraction" in new_type:
                    activity_type = "điểm tham quan"
                elif "karaoke" in new_type or "ktv" in new_type or "kara" in new_type:
                    activity_type = "karaoke"
                elif "bar" in new_type or "pub" in new_type:
                    activity_type = "bar"
                elif "cà phê" in new_type or "coffee" in new_type or "cafe" in new_type:
                    activity_type = "cà phê"
                elif "quán ăn" in new_type or "nhà hàng" in new_type or "restaurant" in new_type:
                    activity_type = "quán ăn"
                else:
                    # Default to "điểm tham quan" if not specified
                    activity_type = "điểm tham quan"
                
                logger.info(f"Detected replace request: '{old_place}' -> '{activity_type}'")
                return (True, old_place, activity_type)
        
        return (False, None, None)
    
    async def _replace_activity_in_itinerary(
        self,
        previous_itinerary: dict,
        old_place_name: str,
        new_activity_type: str,
        planner_request: dict,
        budget_alloc: dict,
        existing_hotel: dict,
        request_id: str
    ) -> dict:
        """
        Replace a specific activity in the itinerary with a new one of the specified type.
        """
        from app.services.place_service import PlaceService
        
        # Convert frontend format to planner format
        existing_days = previous_itinerary.get("days", [])
        city = planner_request["hard_constraints"]["destination"]
        soft = planner_request["preference_bundle"].soft
        
        # Find the old place in itinerary
        old_place_found = False
        target_day_idx = None
        target_segment_idx = None
        
        planner_days = []
        for day_idx, day_data in enumerate(existing_days):
            segments = []
            for act_idx, activity in enumerate(day_data.get("activities", [])):
                act_name = activity.get("name", "")
                # Check if this is the place to replace (fuzzy match)
                if old_place_name.lower() in act_name.lower() or act_name.lower() in old_place_name.lower():
                    old_place_found = True
                    target_day_idx = day_idx
                    target_segment_idx = act_idx
                    logger.info(f"Found place to replace: '{act_name}' at day {day_idx+1}, activity {act_idx}")
                    # Don't add this segment, we'll replace it
                    continue
                
                # Convert frontend activity to planner segment
                segments.append({
                    "type": "activity",
                    "name": act_name,
                    "address": activity.get("address"),
                    "duration_min": self._parse_duration_to_minutes(activity.get("duration", "60 phút")),
                    "travel_time_min": self._parse_travel_time_to_minutes(activity.get("travelTime")),
                    "estimated_cost_vnd": self._parse_cost_to_vnd(activity.get("cost")),
                    "category": activity.get("icon", "culture"),
                    "rating": activity.get("rating"),
                    "coordinates": None,
                })
            
            planner_days.append({
                "date": day_data.get("date", ""),
                "hotel": existing_hotel,
                "segments": segments
            })
        
        if not old_place_found:
            logger.warning(f"Place '{old_place_name}' not found in itinerary, falling back to add mode")
            # Fallback to add mode
            return await self.add_activities_to_itinerary(
                previous_itinerary,
                planner_request,
                f"thêm {new_activity_type}"
            )
        
        # Search for new activity
        existing_activity_names = set()
        for day in existing_days:
            for activity in day.get("activities", []):
                existing_activity_names.add(activity.get("name", "").lower())
        
        new_activities = await self._search_specific_activity_type(
            activity_type=new_activity_type,
            city=city,
            existing_activity_names=existing_activity_names,
            soft_constraints=soft,
            limit=5  # Get top 5 to choose best replacement
        )
        
        if not new_activities:
            logger.warning(f"No new activities found for type '{new_activity_type}'")
            # Return unchanged itinerary
            return {
                "itinerary_id": previous_itinerary.get("itinerary_id", request_id),
                "budget_allocation": budget_alloc,
                "hotel": existing_hotel,
                "transportation": [],
                "activities": [],
                "days": planner_days,
            }
        
        # Get the best replacement (top result)
        replacement = new_activities[0]
        
        # Calculate travel time from hotel if available
        if existing_hotel and existing_hotel.get("coordinates"):
            hotel_coords = existing_hotel.get("coordinates")
            if isinstance(hotel_coords, dict) and hotel_coords.get("lat") and hotel_coords.get("lng"):
                if replacement.get("coordinates"):
                    legs = [{
                        "origin": hotel_coords,
                        "dest": replacement["coordinates"],
                        "mode": "driving"
                    }]
                    directions = await self.map_agent.handle({
                        "request_id": request_id,
                        "params": {"legs": legs}
                    })
                    if directions.get("payload", {}).get("legs"):
                        replacement["travel_time_min"] = directions["payload"]["legs"][0]["duration_min"]
        
        # Create replacement segment
        replacement_segment = {
            "type": "activity",
            "name": replacement.get("name", ""),
            "address": replacement.get("address"),
            "duration_min": replacement.get("recommended_duration_min", 60),
            "travel_time_min": replacement.get("travel_time_min", 0) or None,
            "estimated_cost_vnd": replacement.get("estimated_cost_vnd", 0),
            "category": replacement.get("category", "attraction"),
            "rating": replacement.get("rating"),
            "coordinates": replacement.get("coordinates"),
        }
        
        # Insert replacement at the same position
        planner_days[target_day_idx]["segments"].insert(target_segment_idx, replacement_segment)
        
        logger.info(f"Replaced '{old_place_name}' with '{replacement.get('name')}' at day {target_day_idx+1}")
        
        # Collect all activities for response
        all_activities = []
        for day in planner_days:
            for seg in day["segments"]:
                if seg["type"] == "activity":
                    all_activities.append({
                        "name": seg["name"],
                        "address": seg.get("address"),
                        "duration_min": seg.get("duration_min", 60),
                        "travel_time_min": seg.get("travel_time_min", 0),
                        "estimated_cost_vnd": seg.get("estimated_cost_vnd", 0),
                        "category": seg.get("category"),
                        "rating": seg.get("rating"),
                        "coordinates": seg.get("coordinates"),
                    })
        
        return {
            "itinerary_id": previous_itinerary.get("itinerary_id", request_id),
            "budget_allocation": budget_alloc,
            "hotel": existing_hotel,
            "transportation": [],
            "activities": all_activities,
            "days": planner_days,
        }

    def _extract_activity_type_from_request(self, modification_request: str) -> Optional[str]:
        """
        Extract specific activity type from modification request.
        Examples: "thêm karaoke" -> "karaoke", "thêm bar" -> "bar", "thêm cà phê" -> "cà phê"
        
        Returns:
            Activity type string or None if not found
        """
        import re
        message_lower = modification_request.lower()
        
        # Map keywords to activity types
        activity_keywords = {
            "karaoke": ["karaoke", "ktv", "kara"],  # Added "kara" as abbreviation
            "bar": ["bar", "quán bar", "pub", "quán pub"],
            "club": ["club", "nightclub", "vũ trường"],
            "cà phê": ["cà phê", "ca phe", "coffee", "cafe", "quán cà phê"],
            "quán ăn": ["quán ăn", "nhà hàng", "restaurant", "food"],
            "điểm tham quan": ["điểm tham quan", "attraction", "địa điểm"],
        }
        
        # Check for each activity type
        for activity_type, keywords in activity_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    logger.info(f"Extracted activity type: {activity_type} from keyword: {keyword}")
                    return activity_type
        
        return None
    
    async def _search_specific_activity_type(
        self,
        activity_type: str,
        city: str,
        existing_activity_names: set,
        soft_constraints: Any,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for specific activity type (e.g., karaoke, bar) in a city.
        Returns normalized and scored activities.
        """
        from app.services.place_service import PlaceService
        from app.core.llm import gpt_preference_score
        from app.models.preference_models import compute_preference_score
        from app.utils.scoring import score_activity_with_hybrid_algorithm
        
        place_service = PlaceService()
        maps_service = self.maps_service
        
        # Map activity type to search query
        query_map = {
            "karaoke": f"karaoke tại {city}",
            "bar": f"bar tại {city}",
            "club": f"nightclub tại {city}",
            "cà phê": f"cà phê tại {city}",
            "quán ăn": f"quán ăn tại {city}",
            "điểm tham quan": f"điểm tham quan tại {city}",
        }
        
        search_query = query_map.get(activity_type, f"{activity_type} tại {city}")
        logger.info(f"Searching for: {search_query}")
        
        # Search places
        places = maps_service.search_places(search_query, limit=limit * 2)  # Get more to filter
        
        if not places:
            logger.warning(f"No places found for query: {search_query}")
            return []
        
        # Normalize places
        normalized_places = place_service._normalize_places(places, city=city)
        
        # Filter out existing activities and places without Vietnamese names
        # Also filter to ensure we only get the requested activity type (e.g., karaoke, not restaurants)
        filtered_places = []
        for place in normalized_places:
            name = place.get("name", "").strip()
            if not name:
                continue
            
            # Check if Vietnamese name (simple check for Vietnamese characters)
            vietnamese_chars = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ')
            has_vietnamese = any(char in vietnamese_chars for char in name)
            if not has_vietnamese:
                continue
            
            # Check if already exists
            if name.lower() in existing_activity_names:
                continue
            
            # IMPORTANT: Filter by activity type to ensure we only get the requested type
            # For karaoke: must have "karaoke", "ktv", or "kara" in name, and NOT be primarily a restaurant
            if activity_type == "karaoke":
                name_lower = name.lower()
                has_karaoke_keyword = "karaoke" in name_lower or "ktv" in name_lower or "kara" in name_lower
                
                # Check category from normalized place
                category = place.get("category", "").lower()
                
                # Exclude if it's categorized as food/restaurant (unless name clearly indicates karaoke)
                is_food_category = category == "food"
                has_restaurant_in_name = any(kw in name_lower for kw in ["nhà hàng", "quán ăn", "restaurant", "food"])
                
                # If it's a food category AND doesn't have karaoke keyword, skip it
                if is_food_category and not has_karaoke_keyword:
                    logger.debug(f"Skipping restaurant without karaoke: {name} (category: {category})")
                    continue
                
                # If name doesn't contain karaoke/ktv/kara, skip it
                if not has_karaoke_keyword:
                    logger.debug(f"Skipping place without karaoke keyword: {name}")
                    continue
            
            # Similar filtering for other activity types
            elif activity_type == "bar":
                name_lower = name.lower()
                has_bar_keyword = "bar" in name_lower or "pub" in name_lower or "quán bar" in name_lower
                category = place.get("category", "").lower()
                
                # Exclude restaurants unless name clearly indicates bar/pub
                is_food_category = category == "food"
                if is_food_category and not has_bar_keyword:
                    continue
                if not has_bar_keyword:
                    continue
            
            elif activity_type == "cà phê":
                name_lower = name.lower()
                has_coffee_keyword = any(kw in name_lower for kw in ["cà phê", "ca phe", "coffee", "cafe"])
                if not has_coffee_keyword:
                    continue
            
            filtered_places.append(place)
        
        logger.info(f"Found {len(filtered_places)} new places after filtering")
        
        # Score and rank activities
        scored_activities = []
        activity_budget = 200000  # Default activity budget
        
        for place in filtered_places[:limit]:
            # GPT preference score
            gpt_score = gpt_preference_score(
                activity=place,
                soft_constraints=soft_constraints.dict() if hasattr(soft_constraints, 'dict') else soft_constraints,
                long_term_preferences={},
            )
            
            # Preference score
            pref_score = compute_preference_score(
                activity=place,
                gpt_score=gpt_score,
                soft=soft_constraints,
            )
            
            # Hybrid scoring
            algo_score = score_activity_with_hybrid_algorithm(
                place=place,
                preference_score=pref_score.final_score,
                energy=soft_constraints.energy if hasattr(soft_constraints, 'energy') else "medium",
                activity_budget=activity_budget,
                travel_time_min=0,  # Will be calculated later
            )
            
            place.update({
                "gpt_pref_score": gpt_score,
                "pref_score_components": pref_score.dict() if hasattr(pref_score, 'dict') else {},
                "algo_score": algo_score,
                "recommended_duration_min": place.get("duration_min", 60),
                "travel_time_min": 0,
            })
            
            scored_activities.append(place)
        
        # Sort by algo_score
        scored_activities.sort(key=lambda x: x.get("algo_score", 0), reverse=True)
        
        return scored_activities

    async def _calculate_travel_times_between_segments(self, segments: list, mode: str = "driving") -> list:
        """
        Calculate travel time and distance between consecutive activity segments.
        Adds travelTimeToNext (minutes) and distanceToNext (meters) to each segment.
        
        Args:
            segments: List of segment dictionaries
            mode: Transportation mode (driving, walking, bicycling, transit)
        
        Returns:
            Updated segments with travelTimeToNext and distanceToNext
        """
        # Auto set mode = "driving" if not specified or invalid
        if not mode or not isinstance(mode, str) or mode.strip() == "":
            mode = "driving"
        
        if len(segments) < 2:
            # No travel time needed if less than 2 segments
            return segments
        
        # Find pairs of consecutive activities with coordinates
        origins = []
        destinations = []
        segment_indices = []  # Track which segment pairs we're calculating
        
        for i in range(len(segments) - 1):
            current_seg = segments[i]
            next_seg = segments[i + 1]
            
            # Only calculate if both segments are activities with coordinates
            if (current_seg.get("type") == "activity" and 
                next_seg.get("type") == "activity" and
                current_seg.get("coordinates") and 
                next_seg.get("coordinates") and
                current_seg["coordinates"].get("lat") and 
                current_seg["coordinates"].get("lng") and
                next_seg["coordinates"].get("lat") and 
                next_seg["coordinates"].get("lng")):
                
                origins.append(current_seg["coordinates"])
                destinations.append(next_seg["coordinates"])
                segment_indices.append(i)
        
        if not origins:
            # No valid coordinate pairs, return segments as-is
            return segments
        
        # Batch calculate travel times using Distance Matrix API
        try:
            results = self.maps_service.get_distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=mode
            )
            
            # Update segments with travel time information
            for idx, result in zip(segment_indices, results):
                travel_time_seconds = result.get("travelTime", 0)
                distance_meters = result.get("distance", 0)
                travel_time_minutes = travel_time_seconds // 60
                
                segments[idx]["travelTimeToNext"] = travel_time_minutes
                segments[idx]["distanceToNext"] = distance_meters
                
                logger.debug(f"Travel time from '{segments[idx].get('name')}' to '{segments[idx+1].get('name')}': {travel_time_minutes} min, {distance_meters}m")
        except Exception as e:
            logger.error(f"Error calculating travel times between segments: {e}")
            # On error, set default values
            for idx in segment_indices:
                segments[idx]["travelTimeToNext"] = 0
                segments[idx]["distanceToNext"] = 0
        
        return segments
