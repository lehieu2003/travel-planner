# backend/app/services/place_service.py

import re
import unicodedata
from typing import List, Dict, Any, Set
from app.services.google_maps_service import GoogleMapsService
from app.core.logger import logger


class PlaceService:

    # Estimated stay duration per category (minutes)
    CATEGORY_DURATION_MAP = {
        "attraction": 120,
        "food": 75,
        "drink": 60,
        "museum": 150,
        "park": 90,
        "shopping": 120,
        "landmark": 90,
        "viewpoint": 60,
        "natural": 120,
        "temple": 90
    }

    # priceLevel → estimated VND cost
    PRICELEVEL_COST_MAP = {
        0: 0,
        1: 100000,     # 100k VND
        2: 250000,
        3: 500000,
        4: 1000000     # luxury
    }

    def __init__(self):
        self.maps = GoogleMapsService()
        
        # Common chain restaurants in Vietnam (normalized names)
        self.chain_restaurants = {
            "haidilao", "highlands coffee", "the coffee house", "trung nguyen",
            "kfc", "mcdonald", "pizza hut", "domino", "lotteria", "burger king",
            "pho 24", "pho 2000", "com tam cali", "banh mi huynh hoa",
            "starbucks", "gong cha", "koi", "tocotoco", "ding tea"
        }

    # -------------------------------------------------------
    # NORMALIZE VIETNAMESE TEXT FOR DEDUPLICATION
    # -------------------------------------------------------
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
    
    def _extract_chain_name(self, name: str) -> str:
        """
        Extract chain restaurant name from place name.
        Returns normalized chain name if it's a chain, otherwise returns normalized place name.
        """
        normalized = self._normalize_vietnamese_text(name)
        
        # Check if name contains any chain restaurant name
        for chain in self.chain_restaurants:
            chain_normalized = self._normalize_vietnamese_text(chain)
            if chain_normalized in normalized:
                return chain_normalized
        
        # Not a chain, return normalized name
        return normalized
    
    def _is_irrelevant_place(self, name: str, place_types: List[str] = None) -> bool:
        """
        Check if a place is irrelevant (company, office, service provider, etc.)
        that should not appear in travel plans.
        
        Args:
            name: Place name
            place_types: List of Google Places types
        
        Returns:
            True if place is irrelevant and should be filtered out
        """
        if not name:
            return False
        
        # Normalize name for checking
        name_normalized = self._normalize_vietnamese_text(name)
        
        # Keywords that indicate irrelevant places (companies, offices, etc.)
        irrelevant_keywords = [
            # Vietnamese company keywords
            "cong ty", "công ty", "congty", "côngty",
            "co phan", "cổ phần", "cophan", "cổphần",
            "dich vu", "dịch vụ", "dichvu", "dịchvụ",
            "van phong", "văn phòng", "vanphong", "vănphòng",
            "tru so", "trụ sở", "truso", "trụsở",
            "chi nhanh", "chi nhánh", "chinhanh", "chinhanh",
            "doanh nghiep", "doanh nghiệp", "doanhnghiep", "doanhnghiệp",
            "to chuc", "tổ chức", "tochuc", "tổchức",
            "co quan", "cơ quan", "coquan", "cơquan",
            "cong ty tnhh", "công ty tnhh",  # Limited liability company
            "cong ty cp", "công ty cp",  # Joint stock company
            # English company keywords
            "company", "corporation", "corp", "ltd", "llc",
            "office", "headquarters", "hq", "branch",
            "enterprise", "organization", "org", "agency",
            "service provider", "service provider",
            "business center", "business center",
            "trading", "import export", "import-export",
        ]
        
        # Check if name contains any irrelevant keyword
        for keyword in irrelevant_keywords:
            if keyword in name_normalized:
                return True
        
        # Check place types - exclude certain business types
        if place_types:
            types_lower = [t.lower() for t in place_types]
            # Exclude if it's only an establishment/point_of_interest without tourist-related types
            if "establishment" in types_lower:
                # If it's just an establishment without restaurant, cafe, tourist_attraction, etc.
                tourist_types = [
                    "restaurant", "cafe", "coffee_shop", "food", "meal_takeaway",
                    "tourist_attraction", "museum", "park", "zoo", "aquarium",
                    "amusement_park", "art_gallery", "church", "hindu_temple",
                    "mosque", "synagogue", "shopping_mall", "beach", "bar",
                    "night_club", "bakery", "point_of_interest"
                ]
                # If it has establishment but no tourist-related types, it's likely a company/office
                if not any(t in types_lower for t in tourist_types):
                    return True
        
        return False

    # -------------------------------------------------------
    # CATEGORY INFERENCE
    # -------------------------------------------------------
    def _infer_category_from_types(self, place_types: List[str], name: str) -> str:
        """
        Infer category from Google Places types array.
        Priority: cafe > restaurant/food > tourist_attraction > others
        """
        if not place_types:
            return self._infer_category(name)
        
        types_lower = [t.lower() for t in place_types]
        
        # Drink places (cafe, coffee shops, bars, etc.) - highest priority
        if any(t in types_lower for t in ["cafe", "coffee_shop", "bakery", "bar", "night_club"]):
            return "drink"
        
        # Restaurants and food - second priority
        if any(t in types_lower for t in [
            "restaurant", "food", "meal_takeaway", "meal_delivery",
            "bar", "night_club", "point_of_interest"
        ]):
            # Check if it's actually a restaurant (not just POI)
            if "restaurant" in types_lower or "food" in types_lower:
                return "food"
            # If it's a POI but name suggests food, it's food
            if any(keyword in name.lower() for keyword in ["nhà hàng", "quán ăn", "đồ ăn", "restaurant"]):
                return "food"
        
        # Tourist attractions and sightseeing
        if any(t in types_lower for t in [
            "tourist_attraction", "museum", "park", "zoo", "aquarium",
            "amusement_park", "art_gallery", "church", "hindu_temple",
            "mosque", "synagogue", "shopping_mall", "beach"
        ]):
            if "museum" in types_lower:
                return "museum"
            if "park" in types_lower:
                return "park"
            if "shopping_mall" in types_lower:
                return "shopping"
            if "beach" in types_lower:
                return "attraction"
            return "attraction"
        
        # Fallback to name-based inference
        return self._infer_category(name)
    
    def _infer_category(self, name: str) -> str:
        if not name:
            return "attraction"

        n = name.lower()

        if "cafe" in n or "coffee" in n or "cà phê" in n or "bar" in n or "pub" in n or "trà" in n or "nước" in n or "sinh tố" in n or "nước ép" in n or "trà sữa" in n or "giải khát" in n or "nước mía" in n:
            return "drink"
        if "museum" in n or "bảo tàng" in n:
            return "museum"
        if "park" in n or "công viên" in n or "garden" in n:
            return "park"
        if "mall" in n:
            return "shopping"
        if "restaurant" in n or "quán ăn" in n or "đồ ăn" in n or "nhà hàng" in n:
            return "food"
        if "chùa" in n or "đền" in n or "pagoda" in n or "temple" in n:
            return "temple"
        if "bãi biển" in n or "beach" in n:
            return "attraction"
        if "thác" in n or "waterfall" in n or "hang" in n or "hang động" in n or "cave" in n or "núi" in n or "mountain" in n:
            return "natural"
        if "viewpoint" in n or "điểm ngắm" in n or "vantage" in n:
            return "viewpoint"
        if "landmark" in n or "monument" in n or "địa danh" in n:
            return "landmark"
        if "khu du lịch" in n or "công viên giải trí" in n or "amusement park" in n or "theme park" in n:
            return "attraction"

        return "attraction"

    # -------------------------------------------------------
    # SEARCH CATEGORIES
    # -------------------------------------------------------
    def search_top_attractions(self, city: str, limit=20):
        """
        Search for diverse attractions including tourist spots, amusement parks, and entertainment areas.
        Uses multiple queries to get variety.
        """
        # Multiple queries for attraction variety
        queries = [
            f"địa điểm tham quan tại {city}",
            f"khu du lịch tại {city}",
            f"công viên giải trí tại {city}",
            f"amusement park tại {city}",
            f"theme park tại {city}",
            f"điểm đến nổi tiếng tại {city}",
            f"địa điểm check-in tại {city}",
            f"bãi biển tại {city}",
            f"beach tại {city}",
        ]
        
        all_places = []
        seen_names = set()
        
        for query in queries:
            if len(all_places) >= limit * 2:  # Fetch 2x buffer
                break
            places = self.maps.search_places(query, limit=limit)
            for place in places:
                name = place.get("displayName", {}).get("text", "").strip()
                if not name:
                    continue
                # Normalize name for deduplication
                normalized_name = self._normalize_vietnamese_text(name)
                if normalized_name not in seen_names:
                    seen_names.add(normalized_name)
                    all_places.append(place)
        
        return self._normalize_places(all_places, city=city)

    def search_top_museums(self, city: str, limit=15):
        """Search for museums and cultural sites"""
        places = self.maps.search_places(f"bảo tàng tại {city}", limit=limit)
        return self._normalize_places(places, city=city)

    def search_top_landmarks(self, city: str, limit=15):
        """Search for famous landmarks and monuments"""
        places = self.maps.search_places(f"địa danh nổi tiếng tại {city}", limit=limit)
        return self._normalize_places(places, city=city)

    def search_top_parks(self, city: str, limit=15):
        """Search for parks and gardens"""
        places = self.maps.search_places(f"công viên tại {city}", limit=limit)
        return self._normalize_places(places, city=city)

    def search_top_viewpoints(self, city: str, limit=15):
        """Search for viewpoints and scenic spots"""
        places = self.maps.search_places(f"điểm ngắm cảnh tại {city}", limit=limit)
        return self._normalize_places(places, city=city)

    def search_top_natural_attractions(self, city: str, limit=15):
        """
        Search for natural attractions like waterfalls, caves, mountains.
        Uses multiple queries to get variety.
        """
        # Multiple queries for natural attractions
        queries = [
            f"cảnh quan thiên nhiên tại {city}",
            f"núi tại {city}",
            f"mountain tại {city}",
            f"hang động tại {city}",
            f"cave tại {city}",
            f"thác nước tại {city}",
            f"waterfall tại {city}",
        ]
        
        all_places = []
        seen_names = set()
        
        for query in queries:
            if len(all_places) >= limit * 2:  # Fetch 2x buffer
                break
            places = self.maps.search_places(query, limit=limit)
            for place in places:
                name = place.get("displayName", {}).get("text", "").strip()
                if not name:
                    continue
                # Normalize name for deduplication
                normalized_name = self._normalize_vietnamese_text(name)
                if normalized_name not in seen_names:
                    seen_names.add(normalized_name)
                    all_places.append(place)
        
        return self._normalize_places(all_places, city=city)

    def search_top_temples(self, city: str, limit=10):
        """Search for temples, pagodas, and religious sites"""
        places = self.maps.search_places(f"chùa đền tại {city}", limit=limit)
        return self._normalize_places(places, city=city)

    def search_top_food(self, city: str, limit=15, total_days: int = None):
        """
        Search for diverse food options by using multiple queries to get variety.
        This ensures we get different types of restaurants, not just one chain or type.
        
        NON-NEGOTIABLE RULE: Do not return until we have enough unique restaurants.
        Required: total_days × 3 unique restaurants (breakfast, lunch, dinner per day).
        
        Args:
            city: City name
            limit: Maximum number to return
            total_days: Number of days in trip (required for validation)
        """
        if total_days is None:
            total_days = max(1, limit // 3)  # Estimate days from limit
        
        # Required count: days × 3 (breakfast, lunch, dinner per day)
        required_count = total_days * 3
        min_required = max(required_count, 12)  # At least 12 for short trips
        
        # City-specific food keywords (example for Hanoi, can be expanded)
        city_lower = city.lower()
        local_keywords = []
        
        if "hà nội" in city_lower or "hanoi" in city_lower:
            local_keywords = [
                "phở", "bún chả", "bún bò", "cơm rang", "chả cá",
                "bún đậu", "bánh cuốn", "lẩu", "nộm bò khô", "xôi xéo"
            ]
        elif "hồ chí minh" in city_lower or "hcm" in city_lower or "saigon" in city_lower:
            local_keywords = [
                "cơm tấm", "bánh mì", "hủ tiếu", "bún riêu", "bánh xèo",
                "cháo lòng", "bún bò huế", "bánh canh", "bánh cuốn"
            ]
        else:
            # Generic Vietnamese food keywords
            local_keywords = [
                "phở", "bún", "cơm", "lẩu", "bánh", "chả", "nướng", "hải sản"
            ]
        
        # Expanded queries for more variety - targeting different food types
        queries = [
            f"quán ăn tại {city}",
            f"món địa phương tại {city}",
            f"street food tại {city}",
            f"restaurant tại {city}",
            f"nhà hàng ngon tại {city}",
            f"quán ăn địa phương tại {city}",
            f"món ăn truyền thống tại {city}",
            f"nhà hàng buffet tại {city}",
            f"quán lẩu tại {city}",
            f"nhà hàng BBQ tại {city}",
            f"nhà hàng hải sản tại {city}",
            f"nhà hàng bistro tại {city}",
            f"nhà hàng hotpot tại {city}",
        ]
        
        # Add city-specific queries
        for keyword in local_keywords[:5]:  # Use top 5 local keywords
            queries.append(f"{keyword} tại {city}")
        
        max_attempts = 4  # Hard limit: 4 retries
        radius_multiplier = 1.0
        
        all_normalized = []
        seen_names = set()  # Normalized place names
        seen_chains = set()  # Chain restaurant names (only 1 per chain allowed)
        
        for attempt in range(max_attempts):
            results_per_query = max(15, min_required // len(queries) + 5)
            all_places = []
            
            for query in queries:
                if len(all_places) >= min_required * 3:  # Fetch 3x buffer
                    break
                    
                places = self.maps.search_places(query, limit=results_per_query)
                for place in places:
                    name = place.get("displayName", {}).get("text", "").strip()
                    if not name:
                        continue
                    
                    # Normalize name for deduplication
                    normalized_name = self._normalize_vietnamese_text(name)
                    chain_name = self._extract_chain_name(name)
                    
                    # Skip if exact name duplicate
                    if normalized_name in seen_names:
                        continue
                    
                    # Skip if chain restaurant already seen (only 1 per chain)
                    if chain_name in seen_chains and chain_name in self.chain_restaurants:
                        continue
                    
                    seen_names.add(normalized_name)
                    if chain_name in self.chain_restaurants:
                        seen_chains.add(chain_name)
                    
                    all_places.append(place)
                    
                    if len(all_places) >= min_required * 3:
                        break
            
            # Normalize and filter - this will apply rating >= 4.0, has photos filter
            normalized = self._normalize_places(all_places, force_category="food", city=city)
            
            # Deduplicate again after normalization (in case normalization changed something)
            unique_normalized = []
            unique_seen = set()
            for place in normalized:
                place_name = self._normalize_vietnamese_text(place.get("name", ""))
                place_chain = self._extract_chain_name(place.get("name", ""))
                
                if place_name in unique_seen:
                    continue
                if place_chain in seen_chains and place_chain in self.chain_restaurants:
                    continue
                
                unique_seen.add(place_name)
                if place_chain in self.chain_restaurants:
                    seen_chains.add(place_chain)
                unique_normalized.append(place)
            
            all_normalized.extend(unique_normalized)
            
            # Remove duplicates from all_normalized
            final_normalized = []
            final_seen = set()
            for place in all_normalized:
                place_name = self._normalize_vietnamese_text(place.get("name", ""))
                if place_name not in final_seen:
                    final_seen.add(place_name)
                    final_normalized.append(place)
            
            # Check if we have enough unique restaurants
            if len(final_normalized) >= min_required:
                logger.info(f"Found {len(final_normalized)} unique restaurants (required: {min_required})")
                break
            
            # Otherwise, expand radius and retry
            radius_multiplier *= 1.5
            if attempt < max_attempts - 1:
                logger.warning(
                    f"Only found {len(final_normalized)} unique restaurants (required: {min_required}), "
                    f"expanding search radius (attempt {attempt + 1}/{max_attempts})"
                )
        
        # Final validation: must have at least required_count
        if len(final_normalized) < min_required:
            logger.error(
                f"CRITICAL: Only found {len(final_normalized)} unique restaurants "
                f"(required: {min_required} for {total_days} days). "
                f"Returning what we have, but itinerary may be incomplete."
            )
        
        # Sort by rating desc, then review count desc, then distance
        final_normalized.sort(key=lambda x: (
            -x.get("rating", 0),  # Rating desc
            -x.get("votes", 0),     # Review count desc
            x.get("distance_score", 0)  # Distance asc (lower is better)
        ))
        
        return final_normalized[:limit] if limit else final_normalized

    def search_top_drink(self, city: str, limit=10, total_days: int = None):
        """
        Search for diverse drink places (cafes, coffee shops, bars, etc.) using multiple queries.
        Ensures rich variety of drink options, especially specialty cafés and bars.
        
        NON-NEGOTIABLE RULE: Do not return until we have enough unique drink places.
        Required: total_days × 1 minimum (1-2 per day).
        
        Args:
            city: City name
            limit: Maximum number to return
            total_days: Number of days in trip (required for validation)
        """
        if total_days is None:
            total_days = max(1, limit)
        
        # Required count: days × 1 minimum (1-2 per day)
        required_count = total_days * 1
        min_required = max(required_count, 4)  # At least 4 for short trips
        
        # City-specific drink keywords
        city_lower = city.lower()
        local_keywords = []
        
        if "hà nội" in city_lower or "hanoi" in city_lower:
            local_keywords = ["cà phê trứng", "cafe trứng", "cà phê sách", "quán bar", "pub"]
        elif "hồ chí minh" in city_lower or "hcm" in city_lower or "saigon" in city_lower:
            local_keywords = ["cà phê sữa đá", "cafe sài gòn", "cà phê vỉa hè", "quán bar", "pub"]
        else:
            local_keywords = ["cà phê", "cafe", "quán bar", "pub"]
        
        # Multiple queries for drink variety (coffee, tea, bars, smoothies, juices, etc.)
        queries = [
            f"cafe tại {city}",
            f"coffee tại {city}",
            f"roastery tại {city}",
            f"specialty coffee tại {city}",
            f"quán cafe đẹp tại {city}",
            f"cà phê tại {city}",
            f"coffee shop tại {city}",
            f"quán cà phê tại {city}",
            f"cafe view đẹp tại {city}",
            f"cà phê sách tại {city}",
            f"cafe vintage tại {city}",
            f"cà phê trứng tại {city}",
            f"quán cà phê specialty tại {city}",
            f"bar tại {city}",
            f"pub tại {city}",
            f"quán bar tại {city}",
            f"trà tại {city}",
            f"tea tại {city}",
            f"sinh tố tại {city}",
            f"smoothie tại {city}",
            f"nước ép tại {city}",
            f"juice tại {city}",
            f"trà sữa tại {city}",
            f"bubble tea tại {city}",
            f"giải khát tại {city}",
            f"nước mía tại {city}",
            f"quán giải khát tại {city}",
        ]
        
        # Add city-specific queries
        for keyword in local_keywords:
            queries.append(f"{keyword} tại {city}")
        
        max_attempts = 4  # Hard limit: 4 retries
        radius_multiplier = 1.0
        
        all_normalized = []
        seen_names = set()  # Normalized place names
        seen_chains = set()  # Chain drink places (only 1 per chain allowed)
        
        for attempt in range(max_attempts):
            results_per_query = max(10, min_required // len(queries) + 3)
            all_places = []
            
            for query in queries:
                if len(all_places) >= min_required * 3:  # Fetch 3x buffer
                    break
                    
                places = self.maps.search_places(query, limit=results_per_query)
                for place in places:
                    name = place.get("displayName", {}).get("text", "").strip()
                    if not name:
                        continue
                    
                    # Normalize name for deduplication
                    normalized_name = self._normalize_vietnamese_text(name)
                    chain_name = self._extract_chain_name(name)
                    
                    # Skip if exact name duplicate
                    if normalized_name in seen_names:
                        continue
                    
                    # Skip if chain drink place already seen (only 1 per chain)
                    if chain_name in seen_chains and chain_name in self.chain_restaurants:
                        continue
                    
                    seen_names.add(normalized_name)
                    if chain_name in self.chain_restaurants:
                        seen_chains.add(chain_name)
                    
                    all_places.append(place)
                    
                    if len(all_places) >= min_required * 3:
                        break
            
            # Normalize and filter - this will apply rating >= 4.0, has photos filter
            normalized = self._normalize_places(all_places, force_category="drink", city=city)
            
            # Deduplicate again after normalization
            unique_normalized = []
            unique_seen = set()
            for place in normalized:
                place_name = self._normalize_vietnamese_text(place.get("name", ""))
                place_chain = self._extract_chain_name(place.get("name", ""))
                
                if place_name in unique_seen:
                    continue
                if place_chain in seen_chains and place_chain in self.chain_restaurants:
                    continue
                
                unique_seen.add(place_name)
                if place_chain in self.chain_restaurants:
                    seen_chains.add(place_chain)
                unique_normalized.append(place)
            
            all_normalized.extend(unique_normalized)
            
            # Remove duplicates from all_normalized
            final_normalized = []
            final_seen = set()
            for place in all_normalized:
                place_name = self._normalize_vietnamese_text(place.get("name", ""))
                if place_name not in final_seen:
                    final_seen.add(place_name)
                    final_normalized.append(place)
            
            # Check if we have enough unique drink places
            if len(final_normalized) >= min_required:
                logger.info(f"Found {len(final_normalized)} unique drink places (required: {min_required})")
                break
            
            # Otherwise, expand radius and retry
            radius_multiplier *= 1.5
            if attempt < max_attempts - 1:
                logger.warning(
                    f"Only found {len(final_normalized)} unique drink places (required: {min_required}), "
                    f"expanding search radius (attempt {attempt + 1}/{max_attempts})"
                )
        
        # Final validation: must have at least required_count
        if len(final_normalized) < min_required:
            logger.error(
                f"CRITICAL: Only found {len(final_normalized)} unique drink places "
                f"(required: {min_required} for {total_days} days). "
                f"Returning what we have, but itinerary may be incomplete."
            )
        
        # Sort by rating desc, then review count desc, then distance
        final_normalized.sort(key=lambda x: (
            -x.get("rating", 0),  # Rating desc
            -x.get("votes", 0),     # Review count desc
            x.get("distance_score", 0)  # Distance asc (lower is better)
        ))
        
        return final_normalized[:limit] if limit else final_normalized

    # -------------------------------------------------------
    # NORMALIZE GOOGLE PLACES RESPONSE
    # -------------------------------------------------------
    def _normalize_places(self, places, force_category: str = None, city: str = None) -> List[Dict[str, Any]]:
        """
        Normalize Google Places response with improved filtering and categorization.
        Filters: rating >= 4.0, has photos, not permanently closed, must be in city
        Adds detailed descriptions for food and drink places.
        """
        from app.core.logger import logger
        
        normalized = []

        for p in places:
            name = p.get("displayName", {}).get("text", "")
            if not name:
                continue
            
            place_types = p.get("types", [])
            
            # Filter: Skip irrelevant places (companies, offices, service providers)
            if self._is_irrelevant_place(name, place_types):
                logger.debug(f"Filtering out irrelevant place: '{name}' (company/office/service provider)")
                continue
                
            rating = p.get("rating", 0)
            votes = p.get("userRatingCount", 0)
            price_level = p.get("priceLevel", 0)
            photos = p.get("photos", [])
            business_status = p.get("businessStatus", "")
            address = p.get("formattedAddress", "")

            # Filter: Skip places with rating < 4.2 (enhanced requirement)
            if rating < 4.2:
                continue
            
            # Filter: For major cities (Hà Nội, HCM), require at least 1,000 reviews
            major_cities = ["hà nội", "hanoi", "hồ chí minh", "hcm", "saigon", "sài gòn", "tp. hcm"]
            is_major_city = city and any(mc in city.lower() for mc in major_cities)
            if is_major_city and votes < 1000:
                continue
            
            # Filter: Skip permanently closed places
            if business_status == "CLOSED_PERMANENTLY":
                continue
            
            # Filter: Skip places without photos (hard rule)
            if len(photos) == 0:
                continue
            
            # Infer category from types first, then fallback to name (needed for city check)
            if force_category:
                category = force_category
            else:
                category = self._infer_category_from_types(place_types, name)
            
            # Filter: Must be in city of trip (check address contains city name)
            # STRICT RULE: ALL places MUST be in the correct city (food, drink, activities, attractions, etc.)
            if city and address:
                city_lower = city.lower()
                address_lower = address.lower()
                # Check if city name appears in address
                city_found = city_lower in address_lower
                
                # Also check common city name variations
                if not city_found:
                    city_variations = {
                        "hà nội": ["hanoi", "ha noi", "ha noi"],
                        "hồ chí minh": ["ho chi minh", "hcm", "saigon", "sài gòn", "tp. hcm"],
                        "đà nẵng": ["da nang", "danang"],
                        "hội an": ["hoi an"],
                        "huế": ["hue"],
                        "nha trang": ["nha trang"],
                        "đà lạt": ["da lat", "dalat"],
                    }
                    for key, variations in city_variations.items():
                        if key in city_lower or city_lower in key:
                            if any(var in address_lower for var in variations):
                                city_found = True
                                break
                
                # STRICT: ALL categories MUST be in correct city
                if not city_found:
                    logger.debug(f"Place '{name}' (category: {category}) address '{address}' is not in city '{city}', skipping (strict city requirement)")
                    continue

            # Estimated cost in VND from priceLevel
            estimated_cost = self.PRICELEVEL_COST_MAP.get(price_level, 0)

            # Estimated stay duration
            duration = self.CATEGORY_DURATION_MAP.get(category, 90)

            # Safely extract location coordinates
            location = p.get("location") or {}
            lat = location.get("latitude")
            lng = location.get("longitude")
            
            # Only add place if it has valid coordinates
            if lat is not None and lng is not None:
                # Generate detailed description for food and drink places
                description = self._generate_place_description(
                    name=name,
                    category=category,
                    rating=rating,
                    votes=votes,
                    price_level=price_level,
                    address=address,
                    city=city
                )
                
                # Calculate distance score (normalized, lower is better)
                # For now, we don't have a reference point, so set to 0
                distance_score = 0
                
                # Calculate variety score (unique cuisine bonus)
                variety_score = self._calculate_variety_score(name, place_types, category)
                
                normalized.append({
                    "name": name,
                    "address": address,
                    "price_level": price_level,
                    "estimated_cost_vnd": estimated_cost,

                    "category": category,
                    "duration_min": duration,

                    "rating": rating,
                    "rating_normalized": rating / 5 if rating else 0,
                    "votes": votes,
                    "vote_strength": min(1.0, votes / 1000),
                    "has_photos": len(photos) > 0,
                    "distance_score": distance_score,
                    "variety_score": variety_score,
                    
                    # Detailed description for food and drink
                    "description": description,

                    "coordinates": {
                        "lat": lat,
                        "lng": lng
                    }
                })

        return normalized
    
    def _generate_place_description(self, name: str, category: str, rating: float, 
                                     votes: int, price_level: int, address: str, city: str = None) -> str:
        """
        Generate a detailed description for food and drink places.
        Includes: signature dish/specialty, vibe, price range, recommended time slot.
        One single short line (one paragraph max).
        """
        if category not in ["food", "drink"]:
            return ""
        
        # Price range description
        price_descriptions = {
            0: "giá rẻ",
            1: "giá hợp lý",
            2: "tầm trung",
            3: "cao cấp",
            4: "sang trọng"
        }
        price_desc = price_descriptions.get(price_level, "giá hợp lý")
        
        # Vibe description based on rating and votes
        if rating >= 4.5 and votes >= 500:
            vibe = "nổi tiếng và được đánh giá cao"
        elif rating >= 4.3:
            vibe = "được yêu thích"
        elif rating >= 4.0:
            vibe = "chất lượng tốt"
        else:
            vibe = "đáng thử"
        
        # Recommended time slot
        if category == "food":
            # Try to infer meal type from name
            name_lower = name.lower()
            if any(word in name_lower for word in ["sáng", "breakfast", "bữa sáng"]):
                time_slot = "bữa sáng"
            elif any(word in name_lower for word in ["trưa", "lunch", "bữa trưa"]):
                time_slot = "bữa trưa"
            elif any(word in name_lower for word in ["tối", "dinner", "bữa tối", "đêm"]):
                time_slot = "bữa tối"
            else:
                time_slot = "cả ngày"
        else:  # drink
            time_slot = "sáng hoặc chiều"
        
        # Signature dish/specialty inference from name - make it more specific
        name_lower = name.lower()
        specialty = ""
        
        if category == "food":
            # Vietnamese dishes - be more specific
            if "phở" in name_lower:
                if "bò" in name_lower:
                    specialty = "Phở bò tái chín, nước dùng trong và ngọt xương"
                elif "gà" in name_lower:
                    specialty = "Phở gà thơm ngon, nước dùng đậm đà"
                else:
                    specialty = "Phở bò truyền thống, nước dùng trong và ngọt xương"
            elif "bún chả" in name_lower:
                specialty = "Bún chả truyền thống, thịt nướng thơm lừng và nước chấm đậm đà"
            elif "bún bò" in name_lower:
                specialty = "Bún bò Huế, nước dùng cay nồng và thịt bò mềm"
            elif "chả cá" in name_lower:
                specialty = "Chả cá Lã Vọng, cá nướng thơm và nghệ tươi"
            elif "lẩu" in name_lower:
                if "thái" in name_lower or "tom yum" in name_lower:
                    specialty = "Lẩu Thái chua cay, nước dùng đậm đà"
                elif "hải sản" in name_lower:
                    specialty = "Lẩu hải sản tươi ngon, nước dùng ngọt tự nhiên"
                else:
                    specialty = "Lẩu nóng hổi, nước dùng đậm đà"
            elif "bbq" in name_lower or "nướng" in name_lower:
                specialty = "Đồ nướng tươi ngon, thịt mềm và đậm vị"
            elif "hải sản" in name_lower or "seafood" in name_lower:
                specialty = "Hải sản tươi sống, chế biến đa dạng"
            elif "chay" in name_lower or "vegan" in name_lower:
                specialty = "Món chay thanh đạm, đa dạng và ngon miệng"
            elif "buffet" in name_lower:
                specialty = "Buffet đa dạng, nhiều món ngon"
            elif "bánh mì" in name_lower:
                specialty = "Bánh mì giòn tan, nhân đầy đặn và đậm vị"
            elif "cơm tấm" in name_lower:
                specialty = "Cơm tấm Sài Gòn, sườn nướng thơm và cơm dẻo"
            elif "bánh xèo" in name_lower:
                specialty = "Bánh xèo giòn rụm, nhân tôm thịt đầy đặn"
            else:
                specialty = "Món địa phương đặc trưng, hương vị truyền thống"
        else:  # drink
            if "sinh tố" in name_lower or "smoothie" in name_lower:
                specialty = "Sinh tố tươi ngon, nhiều loại trái cây đa dạng"
            elif "nước ép" in name_lower or "juice" in name_lower:
                specialty = "Nước ép trái cây tươi, nguyên chất và bổ dưỡng"
            elif "trà sữa" in name_lower or "bubble tea" in name_lower:
                specialty = "Trà sữa thơm ngon, nhiều topping đa dạng"
            elif "nước mía" in name_lower:
                specialty = "Nước mía tươi mát, ngọt tự nhiên"
            elif "giải khát" in name_lower:
                specialty = "Quán giải khát với nhiều loại đồ uống mát lạnh"
            elif "trứng" in name_lower:
                specialty = "Cà phê trứng béo ngậy, hương vị đặc biệt"
            elif "roastery" in name_lower or "specialty" in name_lower:
                specialty = "Cà phê specialty, hạt rang tại chỗ và pha chế chuyên nghiệp"
            elif "sách" in name_lower:
                specialty = "Cà phê sách, không gian yên tĩnh và cà phê ngon"
            elif "cold brew" in name_lower:
                specialty = "Cold Brew mát lạnh, hương vị đậm đà"
            elif "bar" in name_lower or "pub" in name_lower:
                specialty = "Quán bar với nhiều loại đồ uống đa dạng, không gian thoải mái"
            elif "trà" in name_lower or "tea" in name_lower:
                specialty = "Trà thơm ngon, nhiều loại trà đặc biệt"
            else:
                specialty = "Đồ uống đa dạng, pha chế chuyên nghiệp"
        
        # Build description
        if category == "food":
            description = f"Quán nổi tiếng với {specialty} và {vibe}, {price_desc}, phù hợp cho {time_slot}."
        else:  # drink
            description = f"Quán đồ uống với {specialty}, {vibe}, {price_desc}, phù hợp cho {time_slot}."
        
        return description
    
    def _calculate_variety_score(self, name: str, place_types: List[str], category: str) -> float:
        """
        Calculate variety score based on unique cuisine/category.
        Higher score = more unique/diverse.
        """
        score = 0.0
        
        if category == "food":
            name_lower = name.lower()
            # Bonus for different cuisine types
            cuisine_keywords = {
                "vietnamese": ["phở", "bún", "chả", "địa phương", "truyền thống"],
                "japanese": ["nhật", "japanese", "sushi", "ramen"],
                "korean": ["hàn", "korean", "bbq"],
                "seafood": ["hải sản", "seafood"],
                "vegetarian": ["chay", "vegan"],
                "street_food": ["street", "vỉa hè"],
                "dessert": ["dessert", "tráng miệng", "bánh"],
            }
            
            for cuisine_type, keywords in cuisine_keywords.items():
                if any(kw in name_lower for kw in keywords):
                    score += 0.1
                    break
        
        elif category == "drink":
            name_lower = name.lower()
            # Bonus for specialty drink types
            if "specialty" in name_lower or "roastery" in name_lower:
                score += 0.2
            elif "sinh tố" in name_lower or "smoothie" in name_lower:
                score += 0.15
            elif "nước ép" in name_lower or "juice" in name_lower:
                score += 0.15
            elif "trà sữa" in name_lower or "bubble tea" in name_lower:
                score += 0.15
            elif "trứng" in name_lower:
                score += 0.15
            elif "nước mía" in name_lower:
                score += 0.1
            elif "sách" in name_lower or "vintage" in name_lower:
                score += 0.1
            elif "bar" in name_lower or "pub" in name_lower:
                score += 0.1
            elif "giải khát" in name_lower:
                score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
