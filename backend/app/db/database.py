from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def _build_supabase_client() -> Any:
    """
    Lazy Supabase client initialization.

    Kept lazy to avoid import-time failures when env vars are not configured yet.
    """

    if not settings.SUPABASE_URL:
        # Allow the app to start in environments where Supabase isn't configured.
        return None

    # Prefer service-role for privileged writes; fall back to anon key for reads.
    if settings.SUPABASE_SERVICE_ROLE_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    if settings.SUPABASE_ANON_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    return None


def get_supabase_client() -> Any:
    """
    Supabase client retrieval.

    Kept sync for simplicity because the project scaffold uses sync auth endpoints
    and unit tests rely on straightforward call semantics.
    """

    return _build_supabase_client()

