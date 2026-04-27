"""Interests-related schemas (mostly passthrough)."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class Interest(BaseModel):
    id: Optional[str] = None
    nombre: Optional[str] = None


class InterestListResponse(BaseModel):
    items: List[Any] = []
