from fastapi import Header, HTTPException, status


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


async def get_bearer_token(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    token = _parse_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


async def get_optional_bearer_token(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str | None:
    return _parse_bearer(authorization)
