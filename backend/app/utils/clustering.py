# backend/app/utils/clustering.py

from typing import List, Dict, Any


def determine_hotel_zone(activities: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Simple centroid of top activities.
    Can be replaced by KMeans later.

    Returns:
        {"lat": ..., "lng": ...}
    """

    if not activities:
        return {"lat": 10.7769, "lng": 106.7009}  # default HCMC District 1

    lat_total = 0.0
    lng_total = 0.0
    count = 0

    for a in activities[:10]:
        coords = a.get("coordinates")
        if coords and coords.get("lat") and coords.get("lng"):
            lat_total += coords["lat"]
            lng_total += coords["lng"]
            count += 1

    if count == 0:
        return {"lat": 10.7769, "lng": 106.7009}

    return {
        "lat": lat_total / count,
        "lng": lng_total / count,
    }
