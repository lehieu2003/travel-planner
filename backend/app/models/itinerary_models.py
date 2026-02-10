# backend/app/models/itinerary_models.py

from pydantic import BaseModel
from typing import Dict, Any, Optional


class SaveItineraryIn(BaseModel):
    title: str
    payload: Dict[str, Any]


class ItineraryOut(BaseModel):
    id: int
    title: str
    payload: Dict[str, Any]
    created_at: str
