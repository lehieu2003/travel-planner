# backend/app/api/routes_profile.py

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.db.sqlite_memory import SQLiteMemory
from app.core.security import decode_token

db = SQLiteMemory()
router = APIRouter(prefix="/profile", tags=["profile"])


# --------------------------------------------------------
# Helper → Get user_id from JWT
# --------------------------------------------------------
def _get_user_id(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    return payload.get("sub") if payload else None


# --------------------------------------------------------
# Pydantic Models
# --------------------------------------------------------
class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None

    age: Optional[int] = None
    gender: Optional[str] = None            # male / female / other
    energy_level: Optional[str] = None      # low / medium / high

    budget_min: Optional[int] = None
    budget_max: Optional[int] = None

    preferences: Optional[List[str]] = None # tags: ["food", "coffee", "museum"]

    # optional long-term memory override
    long_term: Optional[Dict[str, Any]] = None


class ProfileOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    energy_level: Optional[str]
    budget_min: Optional[int]
    budget_max: Optional[int]
    preferences: Optional[List[str]]
    stats: Dict[str, Any]


# --------------------------------------------------------
# GET /profile  → View current profile
# --------------------------------------------------------
@router.get("/", response_model=ProfileOut)
def get_profile(authorization: Optional[str] = Header(None)):

    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    cur = db.conn.cursor()
    cur.execute("""
        SELECT id, email, full_name, age, gender, energy_level,
               budget_min, budget_max, preferences_json
        FROM users
        WHERE id = ?
    """, (int(user_id),))
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    # Load preferences JSON
    prefs = []
    if row["preferences_json"]:
        import json
        try:
            prefs = json.loads(row["preferences_json"])
        except:
            prefs = []

    # Stats → from itineraries + long-term memory
    long_memory = db.get_long_memory(str(user_id)) or {}

    cur.execute("SELECT COUNT(*) as count FROM itineraries WHERE user_id = ?", (str(user_id),))
    saved_itineraries = cur.fetchone()["count"]

    stats = {
        "tripsPlanned": long_memory.get("trips_planned", 0),
        "placesVisited": long_memory.get("places_visited", 0),
        "savedItineraries": saved_itineraries
    }

    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "age": row["age"],
        "gender": row["gender"],
        "energy_level": row["energy_level"],
        "budget_min": row["budget_min"],
        "budget_max": row["budget_max"],
        "preferences": prefs,
        "stats": stats,
    }


# --------------------------------------------------------
# POST /profile/update  → Update user profile
# --------------------------------------------------------
@router.post("/update", response_model=ProfileOut)
def update_profile(data: ProfileUpdate, authorization: Optional[str] = Header(None)):

    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch current user
    cur = db.conn.cursor()
    cur.execute("""
        SELECT id, email, full_name, age, gender, energy_level,
               budget_min, budget_max, preferences_json
        FROM users
        WHERE id = ?
    """, (int(user_id),))
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    # --------------------------------------------------------
    # Update DB — dynamic update per field provided
    # --------------------------------------------------------
    updates = {
        "full_name": data.full_name if data.full_name is not None else row["full_name"],
        "age": data.age if data.age is not None else row["age"],
        "gender": data.gender if data.gender is not None else row["gender"],
        "energy_level": data.energy_level if data.energy_level is not None else row["energy_level"],
        "budget_min": data.budget_min if data.budget_min is not None else row["budget_min"],
        "budget_max": data.budget_max if data.budget_max is not None else row["budget_max"],
        "preferences_json": row["preferences_json"],
    }

    # Convert preferences back to JSON string
    if data.preferences is not None:
        import json
        updates["preferences_json"] = json.dumps(data.preferences)

    # Execute update
    cur.execute("""
        UPDATE users
        SET full_name = ?, age = ?, gender = ?, energy_level = ?,
            budget_min = ?, budget_max = ?, preferences_json = ?
        WHERE id = ?
    """, (
        updates["full_name"],
        updates["age"],
        updates["gender"],
        updates["energy_level"],
        updates["budget_min"],
        updates["budget_max"],
        updates["preferences_json"],
        int(user_id),
    ))
    db.conn.commit()

    # --------------------------------------------------------
    # Update Long-Term Memory (if provided)
    # --------------------------------------------------------
    if data.long_term:
        db.set_long_memory(user_id, data.long_term)

    # Reload updated row
    return get_profile(authorization)
