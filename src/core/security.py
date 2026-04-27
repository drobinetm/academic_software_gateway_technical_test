"""Security helpers (Bearer token extraction)."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, status


def _parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


async def get_bearer_token(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str:
    """Require a Bearer token in the request. Raise 401 if missing/invalid."""
    token = _parse_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


async def get_optional_bearer_token(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Optional[str]:
    """Return the Bearer token if present, otherwise None (no error)."""
    return _parse_bearer(authorization)
