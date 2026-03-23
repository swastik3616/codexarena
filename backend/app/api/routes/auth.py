from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import redis
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password, verify_token
from app.db.database import get_supabase_client
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest


router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_REVOKE_TTL_SECONDS = 7 * 24 * 60 * 60


def get_redis_client() -> Any:
    # decode_responses=True makes values consistently strings in both prod and tests.
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_recruiters_table():
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return client.table("recruiters")


@router.post("/register")
def register(payload: RegisterRequest) -> dict[str, Any]:
    recruiters = _get_recruiters_table()

    # Hash password and insert recruiter
    recruiter_row = recruiters.insert(
        {
            "email": payload.email,
            "name": payload.name,
            "company": payload.company,
            "plan": "free",
            # NOTE: current SQL migrations don’t include password_hash; we still store it
            # for the authentication system. This is also what the unit tests expect.
            "password_hash": hash_password(payload.password),
            "created_at": datetime.now(timezone.utc),
        }
    ).execute().data

    if not recruiter_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed")

    row = recruiter_row[0]
    recruiter_id = str(row["id"])

    jti_access = str(uuid4())
    jti_refresh = str(uuid4())

    access_token = create_access_token({"sub": recruiter_id, "email": payload.email, "jti": jti_access})
    refresh_token = create_refresh_token({"sub": recruiter_id, "email": payload.email, "jti": jti_refresh})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "recruiter": {"id": recruiter_id, "email": payload.email, "name": payload.name},
    }


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    recruiters = _get_recruiters_table()

    res = recruiters.select("*").eq("email", payload.email).single().execute()
    row = res.data
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, row.get("password_hash")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    now = datetime.now(timezone.utc)
    recruiters.update({"last_login_at": now}).eq("id", row["id"]).execute()

    recruiter_id = str(row["id"])
    jti_access = str(uuid4())
    jti_refresh = str(uuid4())

    access_token = create_access_token({"sub": recruiter_id, "email": payload.email, "jti": jti_access})
    refresh_token = create_refresh_token({"sub": recruiter_id, "email": payload.email, "jti": jti_refresh})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "recruiter": {"id": recruiter_id, "email": payload.email, "name": row.get("name")},
    }


@router.post("/refresh")
def refresh(payload: RefreshRequest) -> dict[str, Any]:
    # Verify refresh token (exp included inside verify_token)
    token_payload = verify_token(payload.refresh_token)

    jti = token_payload.get("jti")
    recruiter_id = token_payload.get("sub")
    email = token_payload.get("email")
    if not isinstance(jti, str) or not isinstance(recruiter_id, str) or not isinstance(email, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Single-use refresh tokens: SET NX key to mark token as revoked/used.
    redis_client = get_redis_client()
    revoked_key = f"revoked:{jti}"
    was_set = redis_client.set(revoked_key, 1, nx=True, ex=REFRESH_REVOKE_TTL_SECONDS)
    if not was_set:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reused")

    recruiters = _get_recruiters_table()
    res = recruiters.select("*").eq("id", recruiter_id).single().execute()
    row = res.data
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    jti_access = str(uuid4())
    jti_refresh = str(uuid4())

    access_token = create_access_token({"sub": recruiter_id, "email": email, "jti": jti_access})
    refresh_token = create_refresh_token({"sub": recruiter_id, "email": email, "jti": jti_refresh})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.get("/me")
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return current_user


@router.get("/protected")
def protected(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    # Convenience endpoint for unit tests / verification.
    return current_user

