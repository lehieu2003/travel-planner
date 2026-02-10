# backend/app/agents/activities_agent.py

from typing import Dict, Any, List, Optional
from app.services.place_service import PlaceService
from app.services.google_maps_service import GoogleMapsService
from app.core.llm import gpt_preference_score
from app.core.logger import logger
from app.models.preference_models import (
    UserPreferenceBundle,
    compute_preference_score,
    CATEGORY_KEYWORDS,
)
from app.utils.scoring import score_activity_with_hybrid_algorithm


class ActivitiesAgent:
    """
    Fetch top places (attractions, food, drink) using Google Places API,
    then re-rank using:
        - GPT-nano preference extraction
        - rule-based preference scoring
        - cost alignment
        - energy alignment
        - Algorithm 1: rating + votes + distance + cost penalty
    """

    def __init__(self):
        self.place_service = PlaceService()
        self.maps_service = GoogleMapsService()

    def _has_vietnamese_chars(self, text: str) -> bool:
        """
        Check if text contains Vietnamese characters (accented letters)
        Vietnamese characters include: àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ
        """
        if not text:
            return False
        
        # Vietnamese accented characters
        vietnamese_chars = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ')
        
        # Check if any character in text is Vietnamese
        return any(char in vietnamese_chars for char in text)
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize name for deduplication: lowercase + remove accents + trim
        """
        if not name:
            return ""
        import unicodedata
        import re
        
        # Convert to lowercase
        text = name.lower().strip()
        
        # Normalize Unicode (NFD = Canonical Decomposition)
        text = unicodedata.normalize("NFD", text)
        
        # Remove combining diacritical marks (accents)
        text = re.sub(r'[\u0300-\u036f]', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _preferences_to_search_queries(self, preferences: List[str], city: str) -> List[str]:
        """
        Convert user preferences to search queries for Google Places API.
        Maps preferences to Vietnamese search queries.
        
        Args:
            preferences: List of user preferences (from preferences_json)
            city: City name
        
        Returns:
            List of search query strings
        """
        queries = []
        prefs_lower = [p.lower().strip() for p in preferences if p]
        
        # Map preferences to search queries
        preference_to_query_map = {
            "food": [f"quán ăn tại {city}", f"nhà hàng tại {city}", f"đặc sản tại {city}"],
            "coffee": [f"cà phê tại {city}", f"cafe tại {city}", f"coffee tại {city}"],
            "museum": [f"bảo tàng tại {city}", f"museum tại {city}"],
            "photography": [f"điểm check-in tại {city}", f"địa điểm chụp ảnh tại {city}", f"viewpoint tại {city}"],
            "nightlife": [f"bar tại {city}", f"pub tại {city}", f"club tại {city}", f"karaoke tại {city}"],
            "nature": [f"thiên nhiên tại {city}", f"cảnh quan thiên nhiên tại {city}", f"núi tại {city}"],
            "park": [f"công viên tại {city}", f"park tại {city}"],
            "shopping": [f"trung tâm thương mại tại {city}", f"mall tại {city}", f"shopping tại {city}"],
            "temple": [f"chùa tại {city}", f"đền tại {city}", f"temple tại {city}"],
            "beach": [f"bãi biển tại {city}", f"beach tại {city}"],
            "attraction": [f"địa điểm tham quan tại {city}", f"khu du lịch tại {city}"],
        }
        
        # Direct preference matching
        for pref in prefs_lower:
            # Check exact matches
            if pref in preference_to_query_map:
                queries.extend(preference_to_query_map[pref])
            else:
                # Check partial matches
                for key, query_list in preference_to_query_map.items():
                    if key in pref or pref in key:
                        queries.extend(query_list)
                        break
                # If no match, use preference directly as query
                queries.append(f"{pref} tại {city}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries
    
    def _search_places_by_preferences(
        self,
        preferences: List[str],
        city: str,
        limit_per_query: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Stage 1: Search places using preference keywords FIRST.
        
        Uses preferences to create search queries and fetch relevant places.
        
        Args:
            preferences: List of user preferences (from preferences_json)
            city: City name
            limit_per_query: Maximum results per query
        
        Returns:
            List of places found using preference-based queries
        """
        if not preferences:
            return []
        
        queries = self._preferences_to_search_queries(preferences, city)
        logger.info(f"Searching places using {len(queries)} preference-based queries: {queries[:5]}...")
        
        all_places = []
        seen_names = set()
        
        for query in queries:
            places = self.maps_service.search_places(query, limit=limit_per_query)
            for place in places:
                name = place.get("displayName", {}).get("text", "").strip()
                if not name:
                    continue
                
                # Normalize name for deduplication
                normalized_name = self._normalize_name(name)
                if normalized_name not in seen_names:
                    seen_names.add(normalized_name)
                    all_places.append(place)
        
        logger.info(f"Found {len(all_places)} unique places from preference-based search")
        return all_places

    async def handle(self, planner_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        planner_request must include:
            - preference_bundle  (UserPreferenceBundle)
            - hard_constraints
            - soft_constraints
            - long_memory
        """
        pref_bundle: UserPreferenceBundle = planner_request["preference_bundle"]

        hard = pref_bundle.hard
        soft = pref_bundle.soft
        long_term = pref_bundle.long_term or {}

        city = hard.destination
        total_budget = hard.budget_vnd or 5_000_000

        # Calculate number of days from date constraints
        from datetime import datetime
        total_days = 3  # Default to 3 days
        if hard.date_start and hard.date_end:
            try:
                start = datetime.fromisoformat(hard.date_start)
                end = datetime.fromisoformat(hard.date_end)
                total_days = (end - start).days + 1
            except:
                total_days = 3

        # -----------------------------------------------
        # Dynamic activity budget (spending-style based)
        # -----------------------------------------------
        if soft.spending_style == "budget":
            activity_budget = total_budget * 0.10
        elif soft.spending_style == "premium":
            activity_budget = total_budget * 0.30
        else:
            activity_budget = total_budget * 0.20

        # -----------------------------------------------
        # 1. Stage 1: Search places using preference keywords FIRST
        # -----------------------------------------------
        logger.info(f"Fetching places for city: {city}, budget: {total_budget} VND, {total_days} days")
        
        user_preferences = soft.interests if soft.interests else []
        preference_places = []
        
        if user_preferences:
            # Search places using preference keywords
            logger.info(f"Stage 1: Searching places using preferences: {user_preferences}")
            preference_places_raw = self._search_places_by_preferences(
                preferences=user_preferences,
                city=city,
                limit_per_query=20
            )
            # Normalize preference-based places
            preference_places = self.place_service._normalize_places(preference_places_raw, city=city)
            logger.info(f"Found {len(preference_places)} places from preference-based search")
        
        # -----------------------------------------------
        # 2. Expand with default categories if needed
        # -----------------------------------------------
        # Calculate minimum places needed
        min_places_needed = total_days * 4 + total_days * 4 + total_days * 2  # food + activities + drink
        min_places_needed = max(min_places_needed, 30)
        
        # If we don't have enough preference-based places, expand with default categories
        default_places = []
        if len(preference_places) < min_places_needed:
            logger.info(
                f"Only {len(preference_places)} preference-based places found, "
                f"expanding with default categories (needed: {min_places_needed})"
            )
            
            # Fetch various types of attractions (not food/drink)
            attractions = self.place_service.search_top_attractions(city, limit=15)
            museums = self.place_service.search_top_museums(city, limit=15)
            landmarks = self.place_service.search_top_landmarks(city, limit=15)
            parks = self.place_service.search_top_parks(city, limit=15)
            viewpoints = self.place_service.search_top_viewpoints(city, limit=15)
            natural = self.place_service.search_top_natural_attractions(city, limit=15)
            temples = self.place_service.search_top_temples(city, limit=10)
            
            default_places = attractions + museums + landmarks + parks + viewpoints + natural + temples
            logger.info(f"Found {len(default_places)} places from default categories")
        else:
            logger.info(f"Sufficient preference-based places found ({len(preference_places)}), skipping default categories")
        
        # Food and drink - ALWAYS fetch (required for meals)
        # Required: days × 3 restaurants (breakfast, lunch, dinner per day)
        # Required: days × 1 drink places minimum (1-2 per day)
        required_food_count = total_days * 3
        required_drink_count = total_days * 1
        
        # Fetch with buffer: fetch more than needed to ensure we have enough after filtering
        food_limit = max(required_food_count * 2, 50)  # 2x buffer, minimum 50
        drink_limit = max(required_drink_count * 2, 20)  # 2x buffer, minimum 20
        
        logger.info(f"Fetching food: required {required_food_count} (limit: {food_limit}), drink: required {required_drink_count} (limit: {drink_limit})")
        
        food = self.place_service.search_top_food(city, limit=food_limit, total_days=total_days)
        drink = self.place_service.search_top_drink(city, limit=drink_limit, total_days=total_days)
        
        # VALIDATION: Check if we have enough unique restaurants and drink places
        # Deduplicate food by normalized name
        food_seen = set()
        unique_food = []
        for f in food:
            name = f.get("name", "").strip()
            if not name:
                continue
            # Use simple lowercase for quick check (place_service already normalized)
            name_key = name.lower().strip()
            if name_key not in food_seen:
                food_seen.add(name_key)
                unique_food.append(f)
        
        # Deduplicate drink by normalized name
        drink_seen = set()
        unique_drink = []
        for c in drink:
            name = c.get("name", "").strip()
            if not name:
                continue
            name_key = name.lower().strip()
            if name_key not in drink_seen:
                drink_seen.add(name_key)
                unique_drink.append(c)
        
        # CRITICAL VALIDATION: Must have enough before proceeding
        if len(unique_food) < required_food_count:
            logger.error(
                f"VALIDATION FAILED: Only {len(unique_food)} unique restaurants "
                f"(required: {required_food_count} for {total_days} days). "
                f"Retrying with expanded search..."
            )
            # Retry with larger limit
            food = self.place_service.search_top_food(city, limit=required_food_count * 3, total_days=total_days)
            # Re-deduplicate
            food_seen = set()
            unique_food = []
            for f in food:
                name = f.get("name", "").strip()
                if name:
                    name_key = name.lower().strip()
                    if name_key not in food_seen:
                        food_seen.add(name_key)
                        unique_food.append(f)
        
        if len(unique_drink) < required_drink_count:
            logger.error(
                f"VALIDATION FAILED: Only {len(unique_drink)} unique drink places "
                f"(required: {required_drink_count} for {total_days} days). "
                f"Retrying with expanded search..."
            )
            # Retry with larger limit
            drink = self.place_service.search_top_drink(city, limit=required_drink_count * 3, total_days=total_days)
            # Re-deduplicate
            drink_seen = set()
            unique_drink = []
            for c in drink:
                name = c.get("name", "").strip()
                if name:
                    name_key = name.lower().strip()
                    if name_key not in drink_seen:
                        drink_seen.add(name_key)
                        unique_drink.append(c)
        
        # Final validation check
        if len(unique_food) < required_food_count:
            logger.error(
                f"CRITICAL: Still only {len(unique_food)} unique restaurants "
                f"(required: {required_food_count}). Proceeding with available restaurants."
            )
        else:
            logger.info(f"✓ Validation passed: {len(unique_food)} unique restaurants (required: {required_food_count})")
        
        if len(unique_drink) < required_drink_count:
            logger.error(
                f"CRITICAL: Still only {len(unique_drink)} unique drink places "
                f"(required: {required_drink_count}). Proceeding with available drink places."
            )
        else:
            logger.info(f"✓ Validation passed: {len(unique_drink)} unique drink places (required: {required_drink_count})")
        
        # Use deduplicated lists
        food = unique_food
        drink = unique_drink

        # Combine: preference-based places FIRST (prioritized), then default places, then food/drink
        # Deduplicate preference places and default places
        all_place_names = set()
        combined = []
        
        # Add preference-based places first (highest priority)
        for place in preference_places:
            name = place.get("name", "").strip()
            if not name:
                continue
            normalized = self._normalize_name(name)
            if normalized not in all_place_names:
                all_place_names.add(normalized)
                combined.append(place)
        
        # Add default places (if we expanded)
        for place in default_places:
            name = place.get("name", "").strip()
            if not name:
                continue
            normalized = self._normalize_name(name)
            if normalized not in all_place_names:
                all_place_names.add(normalized)
                combined.append(place)
        
        # Always add food and drink (required for meals)
        combined.extend(food)
        combined.extend(drink)
        
        logger.info(
            f"Combined places: {len(preference_places)} preference-based, "
            f"{len(default_places)} default, {len(food)} food, {len(drink)} drink"
        )
        logger.info(f"Total places before filtering: {len(combined)}")
        
        # Filter to only keep places with Vietnamese names
        combined = [p for p in combined if self._has_vietnamese_chars(p.get("name", ""))]
        logger.info(f"Places with Vietnamese names: {len(combined)}")

        # -----------------------------------------------
        # 3. Smart Budget Filtering (relaxed for multi-day trips)
        # -----------------------------------------------
        filtered: List[Dict[str, Any]] = []
        
        # For multi-day trips, we need more places, so be more lenient
        # Calculate minimum places needed: food (4x days) + other activities (4x days for high energy) + drink (2x days)
        min_places_needed = total_days * 4 + total_days * 4 + total_days * 2  # food + activities + drink
        min_places_needed = max(min_places_needed, 30)  # At least 30 places

        for place in combined:
            cost = place.get("estimated_cost_vnd", 0)

            # Cheap -> always include
            if cost <= activity_budget * 0.10:
                filtered.append(place)
                continue

            # Mid-range -> include if rating decent (lowered threshold for multi-day)
            if cost <= activity_budget * 0.20:
                # Lower rating threshold if we don't have enough places yet
                rating_threshold = 4.0 if len(filtered) < min_places_needed else 4.2
                if place.get("rating", 0) >= rating_threshold:
                    filtered.append(place)
                    continue

            # Expensive -> allow only in special conditions
            if (
                cost <= activity_budget
                and (
                    soft.spending_style == "premium"
                    or (place.get("rating", 0) >= 4.6 and place.get("vote_strength", 0) > 0.5)
                )
            ):
                filtered.append(place)
                continue

        # If we still don't have enough places after filtering, include more mid-range places
        if len(filtered) < min_places_needed:
            logger.info(f"Only {len(filtered)} places after filtering, need {min_places_needed}. Including more mid-range places.")
            filtered_names = {p.get("name", "").lower() for p in filtered}
            for place in combined:
                place_name = place.get("name", "").lower()
                if place_name in filtered_names:
                    continue
                cost = place.get("estimated_cost_vnd", 0)
                # Include mid-range places with lower rating threshold
                if cost <= activity_budget * 0.30 and place.get("rating", 0) >= 3.8:
                    filtered.append(place)
                    filtered_names.add(place_name)
                    if len(filtered) >= min_places_needed:
                        break

        logger.info(f"Places after budget filtering: {len(filtered)} (needed: {min_places_needed})")

        # -----------------------------------------------
        # 4. Calculate Travel Times (if hotel coordinates available)
        # -----------------------------------------------
        # Get hotel coordinates from planner_request if available
        hotel_coords = None
        if "ranked_activities" in planner_request:
            # Hotel might be calculated later, so we'll calculate travel time in orchestrator
            # For now, set travel_time_min to 0
            for place in filtered:
                place["travel_time_min"] = 0
        else:
            # No hotel yet, travel time will be calculated later
            for place in filtered:
                place["travel_time_min"] = 0

        # -----------------------------------------------
        # 5. Stage 2: Hybrid Scoring Algorithm for ALL POIs
        # -----------------------------------------------
        enriched: List[Dict[str, Any]] = []

        for place in filtered:
            # GPT-nano preference score
            gpt_score = gpt_preference_score(
                activity=place,
                soft_constraints=soft.dict(),
                long_term_preferences=long_term,
            )

            # Unified preference score model (UserFit)
            pref_score = compute_preference_score(
                activity=place,
                gpt_score=gpt_score,
                soft=soft,
            )

            # Hybrid Scoring Algorithm: Score = wr·Rating + wp·Popularity + wu·UserFit + wd·DurationFit – λt·TravelTime – λc·CostPenalty
            # Travel time will be updated later in orchestrator, but we can use 0 for initial scoring
            travel_time_min = place.get("travel_time_min", 0) or 0
            
            algo_score = score_activity_with_hybrid_algorithm(
                place=place,
                preference_score=pref_score.final_score,  # UserFit
                energy=soft.energy,
                activity_budget=activity_budget,
                travel_time_min=travel_time_min,  # TravelTime (will be updated later)
            )

            # attach enriched metadata
            place.update(
                {
                    "gpt_pref_score": gpt_score,
                    "pref_score_components": pref_score.dict(),
                    "algo_score": algo_score,
                    "recommended_duration_min": place["duration_min"],
                    "travel_time_min": travel_time_min,  # Store travel time
                }
            )

            enriched.append(place)

        # -----------------------------------------------
        # 4. Sort and return
        # -----------------------------------------------
        enriched.sort(key=lambda x: x["algo_score"], reverse=True)
        
        # Return more places for multi-day trips to ensure enough for all days
        # Calculate: food (3x days) + activities (4x days for high energy) + drink (1x days) + buffer
        # For 4 days: 3*4 + 4*4 + 1*4 = 12 + 16 + 4 = 32, add 50% buffer = 48, minimum 80
        return_limit = max(80, int(total_days * 10))  # At least 10 places per day, minimum 80
        
        logger.info(f"Final enriched activities: {len(enriched)}, returning top {return_limit}")

        return {
            "status": "ok",
            "payload": {
                "ranked": enriched[:return_limit],  # Return more for multi-day trips
                "activity_budget_vnd": activity_budget,
            },
        }
