from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import verify_token
from app.db.database import get_supabase_client


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    Verify JWT, fetch recruiter from DB, return recruiter dict.
    Raises 401 if invalid/expired or user not found.
    """

    try:
        payload = verify_token(token)
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

    recruiter_id = payload.get("sub")
    email = payload.get("email")
    if not isinstance(recruiter_id, str) or not recruiter_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    if not isinstance(email, str) or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token email")

    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    recruiters = client.table("recruiters").select("*").eq("id", recruiter_id).single()
    res = recruiters.execute()
    row = res.data
    if not row:
        # Normalize missing cases to the same 401 expected by tests.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Return recruiter dict (typed shape expected by tests)
    return {
        "id": str(row.get("id")),
        "email": row.get("email"),
        "name": row.get("name"),
    }


async def get_current_candidate(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    Verify a candidate JWT (role=candidate) without DB lookups.
    """

    try:
        payload = verify_token(token)
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

    if payload.get("role") != "candidate":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a candidate token")

    candidate_id = payload.get("sub")
    email = payload.get("email")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    if not isinstance(email, str):
        email = ""

    return {"id": candidate_id, "email": email, "role": "candidate"}


async def get_current_candidate_or_recruiter(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    Verify JWT and return either:
      - candidate dict (role=candidate)
      - recruiter dict (fetched from DB)
    """

    try:
        payload = verify_token(token)
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

    if payload.get("role") == "candidate":
        return await get_current_candidate(token=token)

    # Otherwise treat as recruiter token.
    return await get_current_user(token=token)

