# backend/app/services/flight_service.py

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.serpapi_service import SerpAPIService


class FlightService:
    def __init__(self):
        self.serpapi = SerpAPIService()

    def search_flights(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        children: int = 0,
        currency: str = "VND",
        gl: str = "vn",  # country code for Vietnam
        hl: str = "vi",  # language code for Vietnamese
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search flights using SerpAPI Google Flights API.
        
        Args:
            origin: Departure airport IATA code (e.g., "SGN", "HAN") or city name
            destination: Arrival airport IATA code (e.g., "DAD", "PQC") or city name
            outbound_date: Departure date in YYYY-MM-DD format
            return_date: Optional return date in YYYY-MM-DD format (for round trip)
            adults: Number of adults (default: 1)
            children: Number of children (default: 0)
            currency: Currency code (default: "VND")
            gl: Country code for Google (default: "vn")
            hl: Language code (default: "vi")
            limit: Maximum number of results to return
            
        Returns:
            List of flight dictionaries
        """
        # Validate date format
        try:
            datetime.strptime(outbound_date, "%Y-%m-%d")
            if return_date:
                datetime.strptime(return_date, "%Y-%m-%d")
        except ValueError:
            return []

        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": outbound_date,
            "adults": adults,
            "children": children,
            "currency": currency,
            "gl": gl,
            "hl": hl
        }

        # Add return date if provided (round trip)
        if return_date:
            params["return_date"] = return_date

        raw = self.serpapi.query(params)

        if "error" in raw:
            return []

        results = []
        
        # Handle best_flights (recommended flights)
        best_flights = raw.get("best_flights", [])
        for f in best_flights[:limit]:
            flights = f.get("flights", [])
            if not flights:
                continue
                
            # Get first flight segment for main info
            first_flight = flights[0] if flights else {}
            
            # Extract price
            price_info = f.get("price", {})
            price = (
                price_info.get("extracted_price") or
                price_info.get("price") or
                0
            )
            
            # If price is string, try to extract number
            if isinstance(price, str):
                import re
                numbers = re.findall(r'[\d.]+', price.replace(",", "").replace(".", ""))
                if numbers:
                    try:
                        price = float(numbers[0])
                        if currency == "VND" and price < 100000:
                            price = price * 1000000
                    except ValueError:
                        price = 0

            results.append({
                "airline": first_flight.get("airline", ""),
                "departure_airport": first_flight.get("departure_airport", {}).get("id", ""),
                "arrival_airport": first_flight.get("arrival_airport", {}).get("id", ""),
                "departure_time": first_flight.get("departure_airport", {}).get("time", ""),
                "arrival_time": first_flight.get("arrival_airport", {}).get("time", ""),
                "duration": f.get("total_duration", first_flight.get("duration", "")),
                "price": int(price) if price else 0,
                "stops": f.get("stops", 0),
                "layovers": f.get("layovers", []),
                "flight_number": first_flight.get("flight_number", ""),
                "aircraft": first_flight.get("aircraft", ""),
                "link": f.get("link", "")
            })

        # If no best_flights, try other_flights
        if not results:
            other_flights = raw.get("other_flights", [])
            for f in other_flights[:limit]:
                flights = f.get("flights", [])
                if not flights:
                    continue
                    
                first_flight = flights[0] if flights else {}
                price_info = f.get("price", {})
                price = price_info.get("extracted_price") or price_info.get("price") or 0
                
                if isinstance(price, str):
                    import re
                    numbers = re.findall(r'[\d.]+', price.replace(",", "").replace(".", ""))
                    if numbers:
                        try:
                            price = float(numbers[0])
                            if currency == "VND" and price < 100000:
                                price = price * 1000000
                        except ValueError:
                            price = 0

                results.append({
                    "airline": first_flight.get("airline", ""),
                    "departure_airport": first_flight.get("departure_airport", {}).get("id", ""),
                    "arrival_airport": first_flight.get("arrival_airport", {}).get("id", ""),
                    "departure_time": first_flight.get("departure_airport", {}).get("time", ""),
                    "arrival_time": first_flight.get("arrival_airport", {}).get("time", ""),
                    "duration": f.get("total_duration", first_flight.get("duration", "")),
                    "price": int(price) if price else 0,
                    "stops": f.get("stops", 0),
                    "layovers": f.get("layovers", []),
                    "flight_number": first_flight.get("flight_number", ""),
                    "aircraft": first_flight.get("aircraft", ""),
                    "link": f.get("link", "")
                })

        return results
