from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt

try:
    # passlib is part of the requested stack, but in some environments its bcrypt
    # backend can be incompatible with the installed `bcrypt` wheel.
    from passlib.context import CryptContext
except Exception:  # pragma: no cover
    CryptContext = None  # type: ignore

import bcrypt

from app.core.config import settings


pwd_context = None
if CryptContext is not None:
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    except Exception:  # pragma: no cover
        pwd_context = None

REFRESH_TOKEN_EXPIRE_DAYS: int = 7


def hash_password(password: str) -> str:
    if pwd_context is not None:
        try:
            return pwd_context.hash(password)
        except Exception:
            # Fallback when passlib bcrypt backend is unusable.
            pass

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not isinstance(hashed, str) or not hashed:
        return False
    if pwd_context is not None:
        try:
            return pwd_context.verify(plain, hashed)
        except Exception:
            pass
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _build_token_payload(data: dict[str, Any], *, expires_in: timedelta) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    exp_dt = now + expires_in
    exp = int(exp_dt.timestamp())

    # Required JWT payload fields
    sub = data.get("sub")
    email = data.get("email")
    jti = data.get("jti") or str(uuid4())

    if not isinstance(sub, (str, int)) or not sub:
        raise ValueError("Missing token subject 'sub'")
    if not isinstance(email, str) or not email:
        raise ValueError("Missing token email 'email'")

    return {
        "sub": str(sub),
        "email": email,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": exp,
    }


def create_access_token(data: dict) -> str:
    """
    Create an access token:
    - HS256
    - expiry from settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    - payload includes: sub, email, jti, exp
    """

    payload = _build_token_payload(
        data, expires_in=timedelta(minutes=max(1, int(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)))
    )
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    """
    Create a refresh token:
    - HS256
    - expires in exactly 7 days
    - payload includes: sub, email, jti, exp
    """

    payload = _build_token_payload(data, expires_in=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> dict:
    """
    Verify JWT access/refresh token.

    Raises:
      - HTTP 401 if invalid or expired
    """

    try:
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from e

    # Ensure required fields exist
    required = {"sub", "email", "jti", "exp"}
    if not required.issubset(set(decoded.keys())):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    return decoded

