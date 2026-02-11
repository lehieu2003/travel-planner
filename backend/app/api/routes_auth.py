# backend/app/api/routes_auth.py

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.db.sqlite_memory import SQLiteMemory
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
db = SQLiteMemory()


# --------------------------
# MODELS
# --------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    age: Optional[int] = None
    gender: Optional[str] = None
    energy_level: Optional[str] = "medium"

    budget_min: Optional[int] = 500000   # default 500k VND
    budget_max: Optional[int] = 7000000

    preferences: Optional[list] = []



class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]


# --------------------------
# UTILS
# --------------------------
def get_user_id_from_header(authorization: Optional[str] = Header(None)) -> Optional[int]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    return int(payload["sub"]) if payload else None


# --------------------------
# REGISTER
# --------------------------
@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn):
    existing = db.get_user_by_email(data.email)
    if existing:
        raise HTTPException(400, "Email already registered")

    hashed = get_password_hash(data.password)
    user_id = db.create_user(
        email=data.email,
        full_name=data.full_name or "",
        hashed_password=hashed,
        age=data.age,
        gender=data.gender,
        energy_level=data.energy_level,
        budget_min=data.budget_min,
        budget_max=data.budget_max,
        preferences=data.preferences
    )

    token = create_access_token(subject=str(user_id))
    return {"access_token": token}


# --------------------------
# LOGIN
# --------------------------
@router.post("/login", response_model=TokenOut)
def login(data: LoginIn):
    user = db.get_user_by_email(data.email)
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token(subject=str(user["id"]))
    return {"access_token": token}


# --------------------------
# ME
# --------------------------
@router.get("/me", response_model=MeOut)
def me(authorization: Optional[str] = Header(None)):
    user_id = get_user_id_from_header(authorization)
    if not user_id:
        raise HTTPException(401, "Invalid token")

    cur = db.conn.cursor()
    cur.execute("SELECT id, email, full_name FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "User not found")

    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
    }
