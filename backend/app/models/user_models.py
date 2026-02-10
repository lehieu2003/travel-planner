# backend/app/models/user_models.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any


# -------------------------
# Registration model
# -------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    # New fields
    age: Optional[int] = None
    gender: Optional[str] = None          # male | female | other
    energy_level: Optional[str] = None    # low | medium | high
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    preferences: Optional[List[str]] = []


# -------------------------
# Login model
# -------------------------
class LoginIn(BaseModel):
    email: EmailStr
    password: str


# -------------------------
# Token response
# -------------------------
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------------------------
# Basic user info
# -------------------------
class MeOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_admin: bool


# -------------------------
# Full profile response
# -------------------------
class ProfileOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_admin: bool

    age: Optional[int]
    gender: Optional[str]
    energy_level: Optional[str]

    budget_min: Optional[int]
    budget_max: Optional[int]

    preferences: Optional[List[str]] = []
    stats: Optional[Dict[str, Any]] = None


# -------------------------
# Update profile input
# -------------------------
class UpdateProfileIn(BaseModel):
    full_name: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    energy_level: Optional[str]
    budget_min: Optional[int]
    budget_max: Optional[int]
    preferences: Optional[List[str]] = []
