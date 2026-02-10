# backend/app/agents/accommodation_agent.py

from typing import Dict, Any, List
from app.services.hotel_service import HotelService
from app.utils.clustering import determine_hotel_zone


class AccommodationAgent:
    def __init__(self):
        self.hotel_service = HotelService()

    async def handle(self, planner_request: Dict[str, Any]) -> Dict[str, Any]:
        hard = planner_request["hard_constraints"]
        soft = planner_request.get("soft_constraints", {})
        long_pref = planner_request.get("long_memory", {}).get("preferences", {})

        city = hard["destination"]
        total_budget = hard.get("budget_vnd", 5_000_000)
        start = hard.get("date_start")
        end = hard.get("date_end")

        spending_style = soft.get("spending_style", "balanced")

        # -----------------------------------------------------------
        # 1. Calculate total nights
        # -----------------------------------------------------------
        from datetime import datetime
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        nights = (e - s).days or 1

        # -----------------------------------------------------------
        # 2. Dynamic hotel budget allocation
        # -----------------------------------------------------------
        if spending_style == "budget":
            hotel_budget_ratio = 0.30      # 30% of total budget
        elif spending_style == "premium":
            hotel_budget_ratio = 0.50      # premium users spend a lot on hotel
        else:
            hotel_budget_ratio = 0.40      # balanced default

        total_hotel_budget = total_budget * hotel_budget_ratio
        budget_per_night = total_hotel_budget / nights

        # -----------------------------------------------------------
        # 3. Determine the best hotel zone
        # -----------------------------------------------------------
        activities = planner_request["ranked_activities"]
        zone = determine_hotel_zone(activities)

        # -----------------------------------------------------------
        # 4. Query hotels (SerpAPI)
        # -----------------------------------------------------------
        hotels = self.hotel_service.search_hotels(
            city=city,
            check_in_date=start,
            check_out_date=end,
            budget=budget_per_night,
            latitude=zone["lat"],
            longitude=zone["lng"],
            adults=2,  # Default 2 adults, can be made configurable
            currency="VND",
            limit=30
        )

        enriched_hotels: List[Dict[str, Any]] = []

        # -----------------------------------------------------------
        # 5. Score each hotel dynamically
        # -----------------------------------------------------------
        for h in hotels:
            price = h["price"]
            rating = h.get("rating", 0)
            reviews = h.get("reviews", 0)

            # Cost factor (closer to budget_per_night = better)
            price_score = 1 - min(price / budget_per_night, 1.5)
            price_score = max(0, price_score)  # don't go negative

            # Value score
            value_score = (
                0.6 * (rating / 5) +
                0.3 * min(reviews / 1000, 1.0) +
                0.1 * price_score
            )

            # Premium preference boost
            if spending_style == "premium" and price > budget_per_night:
                value_score += 0.2

            h.update({
                "budget_per_night": budget_per_night,
                "nights": nights,
                "value_score": round(value_score, 4),
                "recommended_duration_min": 45,   # check-in buffer
                "total_cost_vnd": price * nights
            })

            enriched_hotels.append(h)

        # -----------------------------------------------------------
        # 6. Sort by value
        # -----------------------------------------------------------
        enriched_hotels.sort(key=lambda x: x["value_score"], reverse=True)

        # Return top 10
        return {
            "status": "ok",
            "payload": enriched_hotels[:10]
        }
