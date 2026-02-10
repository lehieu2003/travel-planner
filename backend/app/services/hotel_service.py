# backend/app/services/hotel_service.py

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.serpapi_service import SerpAPIService


class HotelService:
    def __init__(self):
        self.serpapi = SerpAPIService()

    def search_hotels(
        self, 
        city: str,
        check_in_date: str,
        check_out_date: str,
        budget: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        adults: int = 2,
        children: int = 0,
        currency: str = "VND",
        gl: str = "vn",  # country code for Vietnam
        hl: str = "vi",  # language code for Vietnamese
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search hotels using SerpAPI Google Hotels API.
        
        Args:
            city: City name (e.g., "Đà Lạt", "Hà Nội")
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            budget: Budget per night in VND
            latitude: Optional latitude for location-based search
            longitude: Optional longitude for location-based search
            adults: Number of adults (default: 2)
            children: Number of children (default: 0)
            currency: Currency code (default: "VND")
            gl: Country code for Google (default: "vn")
            hl: Language code (default: "vi")
            limit: Maximum number of results to return
            
        Returns:
            List of hotel dictionaries
        """
        # Validate date format
        try:
            datetime.strptime(check_in_date, "%Y-%m-%d")
            datetime.strptime(check_out_date, "%Y-%m-%d")
        except ValueError:
            return []

        params = {
            "engine": "google_hotels",
            "q": city,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "children": children,
            "currency": currency,
            "gl": gl,
            "hl": hl
        }

        # Add location parameter if provided (for location-based search)
        if latitude is not None and longitude is not None:
            params["ll"] = f"@{latitude},{longitude},15z"

        raw = self.serpapi.query(params)

        if "error" in raw:
            return []

        hotels = []
        # Handle both "properties" (search results) and single property details
        properties = raw.get("properties", [])
        
        # If single property details returned (when q matches exact hotel name)
        if not properties and raw.get("type") == "hotel":
            properties = [raw]
        
        for h in properties[:limit]:
            # Extract price - can be from rate_per_night or total_rate
            rate_per_night = h.get("rate_per_night", {})
            total_rate = h.get("total_rate", {})
            
            # Try to get extracted price (numeric) first, then fallback to string
            price = (
                rate_per_night.get("extracted_lowest") or
                total_rate.get("extracted_lowest") or
                0
            )
            
            # If extracted price not available, try to parse from string
            if price == 0:
                price_str = rate_per_night.get("lowest") or total_rate.get("lowest", "")
                if price_str:
                    # Try to extract number from string like "$123" or "1.234.567 VNĐ"
                    import re
                    numbers = re.findall(r'[\d.]+', str(price_str).replace(",", "").replace(".", ""))
                    if numbers:
                        try:
                            price = float(numbers[0])
                            # If currency is VND and price seems too low, might be in millions
                            if currency == "VND" and price < 100000:
                                price = price * 1000000
                        except ValueError:
                            pass

            rating = h.get("overall_rating", 0)
            reviews = h.get("reviews", 0)
            gps = h.get("gps_coordinates", {})

            hotels.append({
                "name": h.get("name"),
                "address": h.get("address"),
                "price": int(price) if price else 0,
                "rating": rating,
                "reviews": reviews,
                "within_budget_score": 1 if price and price <= budget else 0,
                "link": h.get("link"),
                "images": h.get("images", []),
                "amenities": h.get("amenities", []),
                "location": {
                    "lat": gps.get("latitude", latitude or 0),
                    "lng": gps.get("longitude", longitude or 0)
                }
            })

        return hotels
