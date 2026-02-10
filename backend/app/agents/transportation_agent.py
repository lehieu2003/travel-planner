# backend/app/agents/transportation_agent.py

from typing import Dict, Any
from app.services.flight_service import FlightService


class TransportationAgent:
    def __init__(self):
        self.flight_service = FlightService()

    async def handle(self, planner_request: Dict[str, Any]) -> Dict[str, Any]:
        hard = planner_request["hard_constraints"]

        origin = hard.get("origin")
        destination = hard.get("destination")
        date_start = hard.get("date_start")
        date_end = hard.get("date_end")

        # If no origin/destination, skip flight search
        if not origin or not destination or not date_start:
            return {
                "status": "ok",
                "payload": []
            }

        flights = self.flight_service.search_flights(
            origin=origin,
            destination=destination,
            outbound_date=date_start,
            return_date=date_end,  # Optional, for round trip
            currency="VND",
            adults=1  # Default, can be made configurable
        )

        return {
            "status": "ok",
            "payload": flights
        }
