# backend/app/agents/map_agent.py

from typing import Dict, Any
from app.services.google_maps_service import GoogleMapsService


class MapAgent:
    def __init__(self):
        self.maps = GoogleMapsService()

    async def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        legs = request["params"]["legs"]

        results = []
        for leg in legs:
            duration = self.maps.get_travel_time(
                origin=leg["origin"],
                destination=leg["dest"],
                mode=leg.get("mode", "driving")
            )
            results.append(duration)

        return {
            "status": "ok",
            "payload": {"legs": results}
        }
