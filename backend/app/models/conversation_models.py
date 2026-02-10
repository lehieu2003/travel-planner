# backend/app/models/conversation_models.py

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ConversationCreateOut(BaseModel):
    id: str
    title: str
    created_at: str


class ConversationListOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageIn(BaseModel):
    content: str
    role: str = "user"    # user | assistant
    conversation_id: Optional[str]


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    itinerary_data: Optional[Dict[str, Any]] = None
