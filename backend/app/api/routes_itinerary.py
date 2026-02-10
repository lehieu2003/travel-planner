# backend/app/api/routes_itinerary.py

from fastapi import APIRouter, Header, HTTPException
from typing import Optional
import json
import hashlib

from app.db.sqlite_memory import SQLiteMemory
from app.core.security import decode_token
from app.models.itinerary_models import SaveItineraryIn, ItineraryOut

router = APIRouter(prefix="/itineraries", tags=["itineraries"])
db = SQLiteMemory()


def get_user_id(auth: Optional[str]) -> int:
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Invalid token")
    payload = decode_token(auth.split(" ")[1])
    return int(payload["sub"]) if payload else None


def generate_itinerary_id(itinerary_data: dict) -> str:
    """Generate a unique ID for itinerary based on its content."""
    # Create a hash from the itinerary content
    content_str = json.dumps(itinerary_data, sort_keys=True)
    return hashlib.md5(content_str.encode()).hexdigest()


def check_duplicate_itinerary(user_id: int, itinerary_data: dict) -> bool:
    """Check if user already saved this exact itinerary."""
    itinerary_id = generate_itinerary_id(itinerary_data)
    saved_itineraries = db.list_itineraries(user_id)
    
    for saved in saved_itineraries:
        saved_id = generate_itinerary_id(saved["payload"])
        if saved_id == itinerary_id:
            return True
    return False


@router.post("/", response_model=ItineraryOut)
def save_itinerary(data: SaveItineraryIn, authorization: Optional[str] = Header(None)):
    """Save an itinerary. Returns the saved itinerary or indicates if it's a duplicate."""
    user_id = get_user_id(authorization)
    
    # Check for duplicate
    if check_duplicate_itinerary(user_id, data.payload):
        raise HTTPException(status_code=409, detail="Itinerary already saved")
    
    # Save itinerary
    itinerary_id = db.save_itinerary(user_id, data.title, data.payload)
    
    # Get the saved itinerary
    saved_itineraries = db.list_itineraries(user_id)
    for it in saved_itineraries:
        if it["id"] == itinerary_id:
            return ItineraryOut(
                id=it["id"],
                title=it["title"],
                payload=it["payload"],
                created_at=it["created_at"]
            )
    
    raise HTTPException(500, "Failed to save itinerary")


@router.get("/")
def list_itineraries(authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)
    items = db.list_itineraries(user_id)
    return {"items": items}


@router.get("/{itinerary_id}")
def get_itinerary(itinerary_id: int, authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)
    rows = db.list_itineraries(user_id)
    for it in rows:
        if it["id"] == itinerary_id:
            return it
    raise HTTPException(404, "Itinerary not found")
