# backend/app/models/planning_models.py

from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class PlannerRequest(BaseModel):
    conversation_id: Optional[str]
    message: str

    user_profile: Optional[Dict[str, Any]] = {}
    constraints: Optional[Dict[str, Any]] = {}
    context: Optional[Dict[str, Any]] = {}


class PlannerResponse(BaseModel):
    itinerary_id: str
    allocations: Dict[str, float]
    activities_scored: List[Dict[str, Any]]
    accommodation: Optional[Dict[str, Any]]
    transportation: Optional[Dict[str, Any]]
    days: List[Dict[str, Any]]
    total_estimated_cost: float
    currency: str = "VND"
