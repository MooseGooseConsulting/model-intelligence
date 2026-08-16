from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceKind(StrEnum):
    API = "api"
    DATASET = "dataset"
    GIT = "git"
    PAGE = "page"
    BROWSER = "browser"
    LOCAL = "local"


class SourceSpec(BaseModel):
    """Stable contract for one upstream observation source."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    kind: SourceKind
    url: HttpUrl
    canonical: bool = True
    expected_content_type: str | None = None
    schema_version: str = "1"


class FetchReceipt(BaseModel):
    """Transport-level evidence retained for every successful source check."""

    source_key: str
    url: str
    fetched_at: datetime
    status_code: int
    etag: str | None = None
    last_modified: str | None = None
    content_type: str | None = None
    body_sha256: str | None = None
    body_bytes: int | None = None
    not_modified: bool = False
    response_headers: dict[str, str] = Field(default_factory=dict)


class SnapshotMeta(BaseModel):
    """Metadata next to an immutable raw source body."""

    source: SourceSpec
    receipt: FetchReceipt
    collector_version: str
    relative_body_path: str
    extra: dict[str, Any] = Field(default_factory=dict)


class SourceState(BaseModel):
    """Mutable check-point used only to avoid unnecessary source downloads."""

    source_key: str
    last_checked_at: datetime
    latest_body_sha256: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    latest_relative_body_path: str | None = None
