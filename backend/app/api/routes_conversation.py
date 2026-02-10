# backend/app/api/routes_conversation.py

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4

from app.db.sqlite_memory import SQLiteMemory
from app.core.security import decode_token

router = APIRouter(prefix="/conversations", tags=["conversations"])
db = SQLiteMemory()


# --------------------------
# Models
# --------------------------
class CreateConversationIn(BaseModel):
    title: Optional[str] = None


# --------------------------
# Utils
# --------------------------
def get_user_id(auth: Optional[str]) -> int:
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Invalid token")
    payload = decode_token(auth.split(" ")[1])
    if not payload:
        raise HTTPException(401, "Invalid token")
    return int(payload["sub"])


# --------------------------
# Create conversation
# --------------------------
@router.post("/create")
def create_conversation(data: CreateConversationIn, authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)

    cid = str(uuid4())
    title = data.title or "Cuộc trò chuyện mới"

    db.create_conversation(cid, str(user_id), title)

    return {"id": cid, "title": title, "created_at": None, "updated_at": None}

# --------------------------
# Create conversation (alternative endpoint for POST /)
# --------------------------
@router.post("/")
def create_conversation_alt(data: CreateConversationIn, authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)

    cid = str(uuid4())
    title = data.title or "Cuộc trò chuyện mới"

    db.create_conversation(cid, str(user_id), title)
    conv = db.get_conversation(cid)

    return conv


# --------------------------
# List conversations
# --------------------------
@router.get("/")
def list_conversations(authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)
    conversations = db.list_conversations(str(user_id))
    # Return array directly for frontend compatibility
    return conversations


# --------------------------
# Get messages for conversation
# --------------------------
@router.get("/{conversation_id}/messages")
def get_messages(conversation_id: str, authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)

    conv = db.get_conversation(conversation_id)
    if not conv or str(conv["user_id"]) != str(user_id):
        raise HTTPException(404, "Conversation not found")

    msgs = db.get_messages(conversation_id)
    # Return array directly for frontend compatibility
    return msgs

# --------------------------
# Update conversation title
# --------------------------
@router.patch("/{conversation_id}/title")
def update_conversation_title(conversation_id: str, data: CreateConversationIn, authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)

    conv = db.get_conversation(conversation_id)
    if not conv or str(conv["user_id"]) != str(user_id):
        raise HTTPException(404, "Conversation not found")

    if not data.title:
        raise HTTPException(400, "Title is required")

    db.update_conversation_title(conversation_id, data.title)
    updated_conv = db.get_conversation(conversation_id)
    return updated_conv

# --------------------------
# Delete conversation
# --------------------------
@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)

    conv = db.get_conversation(conversation_id)
    if not conv or str(conv["user_id"]) != str(user_id):
        raise HTTPException(404, "Conversation not found")

    db.delete_conversation(conversation_id)
    return {"ok": True, "message": "Conversation deleted"}
