# backend/app/core/security.py

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from app.core.config_loader import settings


ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# PASSWORD HASHING
# ---------------------------------------------------------------------------
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT CREATION
# ---------------------------------------------------------------------------
def create_access_token(subject: str, expires_minutes: int = 7 * 24 * 60) -> str:
    """
    Default expiration = 7 days
    """
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded


# ---------------------------------------------------------------------------
# JWT VERIFY
# ---------------------------------------------------------------------------
def decode_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except Exception:
        return None
