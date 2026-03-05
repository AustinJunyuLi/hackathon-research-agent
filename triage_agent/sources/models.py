"""Data models for enrolled research sources."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def _default_include_patterns() -> list[str]:
    return ["*.tex", "*.bib", "*.md"]


def _default_exclude_patterns() -> list[str]:
    return ["*.aux", "*.log", "*.synctex.gz"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SourceType(StrEnum):
    OVERLEAF = "overleaf"
    GITHUB = "github"
    LOCAL = "local"


class EnrolledSource(BaseModel):
    id: str
    type: SourceType
    label: str
    url: str | None = None
    path: str | None = None
    token: str | None = None
    local_mirror: str | None = None
    include: list[str] = Field(default_factory=_default_include_patterns)
    exclude: list[str] = Field(default_factory=_default_exclude_patterns)
    last_synced: datetime | None = None
    enrolled_at: datetime = Field(default_factory=_utc_now)


class SourceRegistry(BaseModel):
    sources: list[EnrolledSource] = Field(default_factory=list)
