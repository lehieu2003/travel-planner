# backend/app/models/agent_models.py

from pydantic import BaseModel
from typing import Dict, Any, Optional, List


class AgentRequest(BaseModel):
    request_id: str
    params: Dict[str, Any]


class ActivitiesResponse(BaseModel):
    ranked: List[Dict[str, Any]]


class AccommodationResponse(BaseModel):
    hotels: List[Dict[str, Any]]


class TransportationResponse(BaseModel):
    flights: List[Dict[str, Any]]


class MapLeg(BaseModel):
    origin: Dict[str, float]
    dest: Dict[str, float]
    duration_min: Optional[int]


class MapResponse(BaseModel):
    legs: List[MapLeg]
