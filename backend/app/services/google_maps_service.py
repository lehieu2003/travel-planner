# backend/app/services/google_maps_service.py

import requests
from typing import Dict, Any, List, Optional, Union
from app.core.config_loader import settings
from app.core.logger import logger


class GoogleMapsService:
    def __init__(self):
        self.key = settings.GOOGLE_MAPS_API_KEY

    # -------------------------------------------------------
    # GOOGLE PLACES SEARCH
    # -------------------------------------------------------
    def search_places(
        self, 
        query: str, 
        location: Optional[Union[str, Dict[str, float]]] = None, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search places using Google Places API Text Search (New)
        
        Args:
            query: Text query (e.g., "pizza in New York")
            location: Optional. Can be:
                - String: city name (e.g., "Đà Lạt") - will be included in query
                - Dict: {"lat": float, "lng": float} - will be used for locationBias
            limit: Maximum number of results (max 60)
        
        Returns:
            List of place objects
        """
        url = "https://places.googleapis.com/v1/places:searchText"

        # Build payload according to Text Search API documentation
        payload = {
            "textQuery": query,
            "maxResultCount": min(limit, 60),  # API max is 60
            "languageCode": "vi"  # Request Vietnamese language for place names
        }

        # Add locationBias if coordinates are provided
        if location and isinstance(location, dict) and "lat" in location and "lng" in location:
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": location["lat"],
                        "longitude": location["lng"]
                    },
                    "radius": 50000.0  # 50km radius in meters
                }
            }
        # If location is a string (city name), it's already in the query text
        # so we don't need locationBias

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key,
            "Accept-Language": "vi",  # Request Vietnamese language in response
            "X-Goog-FieldMask": (
                "places.displayName,"
                "places.formattedAddress,"
                "places.rating,"
                "places.userRatingCount,"
                "places.location,"
                "places.priceLevel,"
                "places.types,"
                "places.photos,"
                "places.businessStatus"
            )
        }

        try:
            logger.debug(f"Searching places with query: {query}, location: {location}")
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            places = data.get("places", [])
            logger.info(f"Found {len(places)} places for query: {query}")
            return places
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error searching places: {e}, Response: {e.response.text if e.response else 'N/A'}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error searching places: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching places: {e}")
            return []

    # -------------------------------------------------------
    # PLACE DETAILS
    # -------------------------------------------------------
    def get_place_details(self, place_id: str):
        url = f"https://places.googleapis.com/v1/places/{place_id}"

        headers = {
            "X-Goog-Api-Key": self.key,
            "Accept-Language": "vi",  # Request Vietnamese language in response
            "X-Goog-FieldMask": "*"
        }
        
        # Add languageCode to query params if supported
        params = {
            "languageCode": "vi"
        }

        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
        except:
            return {}

    # -------------------------------------------------------
    # DIRECTIONS (TRAVEL TIME) - Using Routes API
    # -------------------------------------------------------
    def get_travel_time(self, origin: Dict[str, float], destination: Dict[str, float], mode="driving"):
        """
        Get travel time and distance between two points using Routes API computeRoutes.
        
        Args:
            origin: {"lat": float, "lng": float}
            destination: {"lat": float, "lng": float}
            mode: "driving", "walking", "bicycling", "transit" (default: "driving")
        
        Returns:
            {"duration_min": int, "distance_m": int}
        """
        # Auto set mode = "driving" if not specified or invalid
        if not mode or not isinstance(mode, str) or mode.strip() == "":
            mode = "driving"
        
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        
        # Map mode to Routes API travelMode
        mode_mapping = {
            "driving": "DRIVE",
            "walking": "WALK",
            "bicycling": "BICYCLE",
            "transit": "TRANSIT"
        }
        travel_mode = mode_mapping.get(mode.lower(), "DRIVE")
        
        # Build request body according to Routes API documentation
        payload = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin["lat"],
                        "longitude": origin["lng"]
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination["lat"],
                        "longitude": destination["lng"]
                    }
                }
            },
            "travelMode": travel_mode,
            "routingPreference": "TRAFFIC_AWARE" if travel_mode == "DRIVE" else "DEFAULT_ROUTE_OPTIMIZED",
            "computeAlternativeRoutes": False,
            "languageCode": "vi",
            "units": "METRIC"
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"
        }
        
        try:
            logger.debug(f"Routes API computeRoutes: origin={origin}, destination={destination}, mode={mode}")
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("routes") or len(data["routes"]) == 0:
                logger.warning("Routes API: No routes returned")
                return {"duration_min": 999, "distance_m": 0}
            
            route = data["routes"][0]
            # Handle duration: can be string "3600s" or object {"seconds": 3600}
            duration_value = route.get("duration", "")
            if isinstance(duration_value, str):
                duration_seconds = int(float(duration_value.replace("s", ""))) if duration_value else 0
            elif isinstance(duration_value, dict):
                duration_seconds = int(duration_value.get("seconds", 0))
            else:
                duration_seconds = int(duration_value) if duration_value else 0
            
            duration_min = duration_seconds // 60 if duration_seconds > 0 else 999
            distance_m = route.get("distanceMeters", 0)
            
            logger.debug(f"Routes API: duration={duration_min}min, distance={distance_m}m")
            return {
                "duration_min": duration_min,
                "distance_m": distance_m
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Routes API HTTP error: {e}, Response: {e.response.text if e.response else 'N/A'}")
            return {"duration_min": 999, "distance_m": 0}
        except requests.exceptions.RequestException as e:
            logger.error(f"Routes API request error: {e}")
            return {"duration_min": 999, "distance_m": 0}
        except Exception as e:
            logger.error(f"Routes API unexpected error: {e}")
            return {"duration_min": 999, "distance_m": 0}

    # -------------------------------------------------------
    # DISTANCE MATRIX API (BATCH TRAVEL TIME) - Using Routes API
    # -------------------------------------------------------
    def get_distance_matrix(
        self, 
        origins: List[Dict[str, float]], 
        destinations: List[Dict[str, float]], 
        mode: str = "driving"
    ) -> List[Dict[str, Any]]:
        """
        Get travel time and distance between multiple origin-destination pairs using Routes API computeRouteMatrix.
        
        Args:
            origins: List of {"lat": float, "lng": float}
            destinations: List of {"lat": float, "lng": float}
            mode: "driving", "walking", "bicycling", "transit" (default: "driving")
        
        Returns:
            List of {
                "travelTime": int,  # seconds
                "distance": int,    # meters
                "status": str       # "OK" or error status
            }
        """
        # Auto set mode = "driving" if not specified or invalid
        if not mode or not isinstance(mode, str) or mode.strip() == "":
            mode = "driving"
        
        url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
        
        # Map mode to Routes API travelMode
        mode_mapping = {
            "driving": "DRIVE",
            "walking": "WALK",
            "bicycling": "BICYCLE",
            "transit": "TRANSIT"
        }
        travel_mode = mode_mapping.get(mode.lower(), "DRIVE")
        
        # Build request body according to Routes API documentation
        # Note: computeRouteMatrix API does not support departureTime and trafficModel
        # Use routingPreference: TRAFFIC_AWARE for traffic-aware routing instead
        payload = {
            "origins": [
                {
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": origin["lat"],
                                "longitude": origin["lng"]
                            }
                        }
                    }
                }
                for origin in origins
            ],
            "destinations": [
                {
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": dest["lat"],
                                "longitude": dest["lng"]
                            }
                        }
                    }
                }
                for dest in destinations
            ],
            "travelMode": travel_mode,
            "routingPreference": "TRAFFIC_AWARE" if travel_mode == "DRIVE" else "DEFAULT_ROUTE_OPTIMIZED"
        }
        
        # Note: computeRouteMatrix API does not support departureTime and trafficModel fields
        # The TRAFFIC_AWARE routingPreference will use current traffic conditions
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key,
            "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status,condition"
        }
        
        try:
            logger.debug(f"Routes API computeRouteMatrix: {len(origins)} origins, {len(destinations)} destinations, mode={mode}, travelMode={travel_mode}, routingPreference={payload.get('routingPreference')}")
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            # Log raw response structure for debugging
            logger.debug(f"Routes API response type: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A (not a dict)'}")
            
            # Routes API returns elements array, not rows/elements structure
            # Handle both dict with "elements" key and direct list response
            if isinstance(data, list):
                # API returned list directly
                elements = data
                logger.debug(f"Routes API returned list directly with {len(elements)} elements")
            elif isinstance(data, dict):
                # API returned dict with "elements" key
                elements = data.get("elements", [])
                logger.debug(f"Routes API returned dict with {len(elements)} elements")
            else:
                logger.warning(f"Routes API returned unexpected type: {type(data)}")
                elements = []
            
            # Log raw response for debugging (first few elements only to avoid spam)
            if elements:
                logger.debug(f"Routes API response: {len(elements)} elements returned. First element sample: {elements[0] if elements else 'N/A'}")
            
            if not elements:
                logger.warning("Routes API computeRouteMatrix: No elements returned")
                # Return fallback values
                return [self._estimate_travel_time(
                    origins[i], 
                    destinations[i] if i < len(destinations) else destinations[0] if destinations else origins[i], 
                    mode, 
                    "NO_ELEMENTS"
                ) for i in range(len(origins))]
            
            # Create a mapping from (originIndex, destinationIndex) to result
            # Routes API returns all combinations of origins x destinations
            results_map = {}
            for idx, element in enumerate(elements):
                # Ensure element is a dict before calling .get()
                if not isinstance(element, dict):
                    logger.warning(f"Routes API element {idx} is not a dict: {type(element)}, value: {element}")
                    continue
                
                origin_idx = element.get("originIndex", 0)
                dest_idx = element.get("destinationIndex", 0)
                status = element.get("status", "UNKNOWN_ERROR")
                condition = element.get("condition", "")
                
                # Handle status: can be string "OK" or dict {} (empty dict means OK)
                # Also check condition: "ROUTE_EXISTS" means route is valid
                is_ok = (
                    status == "OK" or 
                    (isinstance(status, dict) and len(status) == 0) or  # Empty dict means OK
                    condition == "ROUTE_EXISTS"
                )
                
                if is_ok:
                    # Handle duration: can be string "3600s" or object {"seconds": 3600}
                    duration_value = element.get("duration", "")
                    if isinstance(duration_value, str):
                        duration_seconds = int(float(duration_value.replace("s", ""))) if duration_value else 0
                    elif isinstance(duration_value, dict):
                        duration_seconds = int(duration_value.get("seconds", 0))
                    else:
                        duration_seconds = int(duration_value) if duration_value else 0
                    
                    distance_meters = element.get("distanceMeters", 0)
                    
                    # Log detailed information for debugging
                    logger.debug(
                        f"Routes API result: origin_idx={origin_idx}, dest_idx={dest_idx}, "
                        f"duration_value={duration_value}, duration_seconds={duration_seconds}, "
                        f"distance_meters={distance_meters}, distance_km={distance_meters/1000:.2f}"
                    )
                    
                    results_map[(origin_idx, dest_idx)] = {
                        "travelTime": duration_seconds,
                        "distance": distance_meters,
                        "status": "OK"
                    }
                else:
                    logger.warning(f"Routes API element status: {status} for origin {origin_idx}, dest {dest_idx}")
                    # Use fallback estimation
                    if origin_idx < len(origins) and dest_idx < len(destinations):
                        results_map[(origin_idx, dest_idx)] = self._estimate_travel_time(
                            origins[origin_idx], destinations[dest_idx], mode, status
                        )
            
            # Build results list matching origins to destinations
            # For 1-to-1 mapping: each origin[i] maps to destination[i]
            # If more origins than destinations, use destination[0] for extra origins
            results = []
            for i in range(len(origins)):
                # Determine which destination to use for this origin
                if i < len(destinations):
                    dest_idx = i  # 1-to-1 mapping
                else:
                    dest_idx = 0  # Use first destination if more origins than destinations
                
                key = (i, dest_idx)
                if key in results_map:
                    results.append(results_map[key])
                else:
                    # Fallback if no matching element
                    target_dest = destinations[dest_idx] if dest_idx < len(destinations) else destinations[0] if destinations else origins[i]
                    results.append(self._estimate_travel_time(origins[i], target_dest, mode, "NO_MATCH"))
            
            logger.info(f"Routes API computeRouteMatrix: Successfully calculated {len(results)} travel times")
            return results
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Routes API computeRouteMatrix HTTP error: {e}, Response: {e.response.text if e.response else 'N/A'}")
            # Return fallback values
            return [self._estimate_travel_time(origins[i], destinations[i] if i < len(destinations) else origins[i], mode, "HTTP_ERROR") 
                   for i in range(len(origins))]
        except requests.exceptions.RequestException as e:
            logger.error(f"Routes API computeRouteMatrix request error: {e}")
            # Return fallback values
            return [self._estimate_travel_time(origins[i], destinations[i] if i < len(destinations) else origins[i], mode, "REQUEST_ERROR") 
                   for i in range(len(origins))]
        except Exception as e:
            logger.error(f"Routes API computeRouteMatrix unexpected error: {e}")
            return [self._estimate_travel_time(origins[i], destinations[i] if i < len(destinations) else origins[i], mode, "UNKNOWN_ERROR") 
                   for i in range(len(origins))]
    
    def _estimate_travel_time(
        self, 
        origin: Dict[str, float], 
        destination: Dict[str, float], 
        mode: str, 
        status: str
    ) -> Dict[str, Any]:
        """
        Fallback: Estimate travel time using simple distance heuristic.
        Uses Haversine formula for distance, then estimates time based on mode.
        """
        import math
        
        # Haversine formula to calculate distance
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(origin["lat"])
        lat2_rad = math.radians(destination["lat"])
        delta_lat = math.radians(destination["lat"] - origin["lat"])
        delta_lng = math.radians(destination["lng"] - origin["lng"])
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_meters = R * c
        
        # Estimate time based on mode (average speeds in m/s)
        if mode == "walking":
            speed_ms = 1.4  # ~5 km/h
        elif mode == "bicycling":
            speed_ms = 4.2  # ~15 km/h
        elif mode == "transit":
            speed_ms = 8.3  # ~30 km/h
        else:  # driving
            speed_ms = 13.9  # ~50 km/h (city average)
        
        estimated_seconds = int(distance_meters / speed_ms)
        
        logger.warning(
            f"⚠️ FALLBACK ESTIMATION USED: origin=({origin['lat']:.6f},{origin['lng']:.6f}), "
            f"destination=({destination['lat']:.6f},{destination['lng']:.6f}), "
            f"distance={distance_meters:.0f}m ({distance_meters/1000:.2f}km), "
            f"estimated_time={estimated_seconds}s ({estimated_seconds//60}min), "
            f"mode={mode}, status={status}"
        )
        
        return {
            "travelTime": estimated_seconds,
            "distance": int(distance_meters),
            "status": f"ESTIMATED_{status}"
        }
