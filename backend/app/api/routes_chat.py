# backend/app/api/routes_chat.py

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import uuid4

from app.agents.llm_agent import LLMAgent
from app.core.security import decode_token
from app.db.sqlite_memory import SQLiteMemory

router = APIRouter(prefix="/chat", tags=["chat"])
llm = LLMAgent()
db = SQLiteMemory()


# -----------------------------
# Helper: extract user_id from Authorization header
# -----------------------------
def _user_id_from_header(authorization: Optional[str]):
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        return None
    return payload.get("sub")


# -----------------------------
# Pydantic request
# -----------------------------
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# -----------------------------
# Chat endpoint - for natural conversation
# -----------------------------
@router.post("", summary="Chat with TravelGPT agent")
async def chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    """
    Chat endpoint that allows natural conversation with the agent.
    This is separate from the planning endpoint and allows the agent
    to ask questions and confirm information before creating plans.
    """
    user_id = _user_id_from_header(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not req.message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Load conversation history if conversation_id provided
    conversation_history = []
    
    if req.conversation_id:
        conversation = db.get_conversation(req.conversation_id)
        if conversation and conversation["user_id"] == user_id:
            messages = db.get_messages(req.conversation_id)
            conversation_history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
        elif conversation and conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this conversation")

    # Add current message to conversation_history for context
    # This ensures the current message is included in the conversation context
    conversation_history.append({
        "role": "user",
        "content": req.message
    })

    # Generate chat response (now includes current message in history)
    try:
        response_text = await llm.generate_chat_response(req.message, conversation_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    # Save messages to conversation
    conversation_id = req.conversation_id
    if not conversation_id:
        # Create new conversation
        conversation_id = str(uuid4())
        title = req.message[:30] + ("..." if len(req.message) > 30 else "")
        db.create_conversation(conversation_id, user_id, title)
    
    # Save user message
    user_message_id = str(uuid4())
    db.add_message(user_message_id, conversation_id, "user", req.message)
    
    # Save assistant message
    assistant_message_id = str(uuid4())
    db.add_message(assistant_message_id, conversation_id, "assistant", response_text)
    
    return {
        "ok": True,
        "conversation_id": conversation_id,
        "message": response_text
    }

