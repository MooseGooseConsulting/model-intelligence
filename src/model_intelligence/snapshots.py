from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Any

from model_intelligence import __version__
from model_intelligence.contracts import FetchReceipt, SnapshotMeta, SourceSpec, SourceState
from model_intelligence.http import HttpFetch


@dataclass(frozen=True, slots=True)
class SnapshotOutcome:
    changed: bool
    not_modified: bool
    body_sha256: str | None
    body_path: Path | None
    metadata_path: Path | None
    state_path: Path


class SnapshotStore:
    """Content-addressed raw evidence plus a tiny mutable validator state.

    Accepted snapshots advance source state. Invalid responses can be quarantined
    without replacing the last known-good ETag/hash checkpoint.
    """

    def __init__(self, root: Path | str = "var") -> None:
        self.root = Path(root)
        self.raw_root = self.root / "raw"
        self.quarantine_root = self.root / "quarantine"
        self.state_root = self.root / "state"

    def read_state(self, source_key: str) -> SourceState | None:
        path = self._state_path(source_key)
        if not path.exists():
            return None
        return SourceState.model_validate_json(path.read_text(encoding="utf-8"))

    def persist(
        self,
        source: SourceSpec,
        fetch: HttpFetch,
        *,
        extra: dict[str, Any] | None = None,
    ) -> SnapshotOutcome:
        prior = self.read_state(source.key)
        state_path = self._state_path(source.key)

        if fetch.not_modified:
            if prior is None:
                raise ValueError(f"{source.key} returned 304 without prior state")
            updated = prior.model_copy(update={"last_checked_at": fetch.fetched_at})
            _atomic_text(state_path, updated.model_dump_json(indent=2))
            return SnapshotOutcome(
                changed=False,
                not_modified=True,
                body_sha256=prior.latest_body_sha256,
                body_path=(self.root / prior.latest_relative_body_path)
                if prior.latest_relative_body_path
                else None,
                metadata_path=None,
                state_path=state_path,
            )

        if fetch.body is None:
            raise ValueError(f"{source.key} returned {fetch.status_code} without a body")

        digest = hashlib.sha256(fetch.body).hexdigest()
        changed = prior is None or prior.latest_body_sha256 != digest
        relative_body = self._relative_body_path("raw", source, fetch, digest)
        body_path = self.root / relative_body
        metadata_path = body_path.with_suffix(body_path.suffix + ".meta.json")

        if changed:
            _atomic_bytes(body_path, fetch.body)
            snapshot_meta = self._snapshot_meta(
                source,
                fetch,
                relative_body,
                digest,
                extra or {},
            )
            _atomic_text(metadata_path, snapshot_meta.model_dump_json(indent=2))

        state = SourceState(
            source_key=source.key,
            last_checked_at=fetch.fetched_at,
            latest_body_sha256=digest,
            etag=fetch.headers.get("etag"),
            last_modified=fetch.headers.get("last-modified"),
            latest_relative_body_path=relative_body.as_posix(),
        )
        _atomic_text(state_path, state.model_dump_json(indent=2))

        return SnapshotOutcome(
            changed=changed,
            not_modified=False,
            body_sha256=digest,
            body_path=body_path,
            metadata_path=metadata_path if changed else None,
            state_path=state_path,
        )

    def quarantine(
        self,
        source: SourceSpec,
        fetch: HttpFetch,
        *,
        reason: str,
        extra: dict[str, Any] | None = None,
    ) -> tuple[Path, Path]:
        """Retain a bad 200-response without advancing accepted source state."""

        if fetch.body is None:
            raise ValueError("Cannot quarantine a response without a body")
        digest = hashlib.sha256(fetch.body).hexdigest()
        relative_body = self._relative_body_path("quarantine", source, fetch, digest)
        body_path = self.root / relative_body
        metadata_path = body_path.with_suffix(body_path.suffix + ".meta.json")
        if not body_path.exists():
            _atomic_bytes(body_path, fetch.body)
        payload = {
            "reason": reason,
            "source": source.model_dump(mode="json"),
            "receipt": self._receipt(source, fetch, digest).model_dump(mode="json"),
            "collector_version": __version__,
            "relative_body_path": relative_body.as_posix(),
            "extra": extra or {},
        }
        _atomic_text(metadata_path, json.dumps(payload, indent=2, sort_keys=True))
        return body_path, metadata_path

    def _snapshot_meta(
        self,
        source: SourceSpec,
        fetch: HttpFetch,
        relative_body: Path,
        digest: str,
        extra: dict[str, Any],
    ) -> SnapshotMeta:
        return SnapshotMeta(
            source=source,
            receipt=self._receipt(source, fetch, digest),
            collector_version=__version__,
            relative_body_path=relative_body.as_posix(),
            extra=extra,
        )

    def _receipt(self, source: SourceSpec, fetch: HttpFetch, digest: str) -> FetchReceipt:
        return FetchReceipt(
            source_key=source.key,
            url=fetch.url,
            fetched_at=fetch.fetched_at,
            status_code=fetch.status_code,
            etag=fetch.headers.get("etag"),
            last_modified=fetch.headers.get("last-modified"),
            content_type=fetch.headers.get("content-type"),
            body_sha256=digest,
            body_bytes=len(fetch.body or b""),
            not_modified=False,
            response_headers=_provenance_headers(fetch.headers),
        )

    def _relative_body_path(
        self,
        bucket: str,
        source: SourceSpec,
        fetch: HttpFetch,
        digest: str,
    ) -> Path:
        day = fetch.fetched_at.astimezone(UTC).strftime("%Y-%m-%d")
        extension = _extension(fetch.headers.get("content-type"))
        return Path(bucket) / source.key / day / f"{digest}{extension}"

    def _state_path(self, source_key: str) -> Path:
        return self.state_root / f"{source_key}.json"


def _extension(content_type: str | None) -> str:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type in {"application/json", "application/problem+json"} or media_type.endswith(
        "+json"
    ):
        return ".json"
    if media_type in {"text/html", "application/xhtml+xml"}:
        return ".html"
    if media_type in {"text/csv", "application/csv"}:
        return ".csv"
    if media_type in {"application/x-parquet", "application/vnd.apache.parquet"}:
        return ".parquet"
    return ".bin"


def _provenance_headers(headers: dict[str, str]) -> dict[str, str]:
    keep = {
        "cache-control",
        "content-type",
        "date",
        "etag",
        "last-modified",
        "retry-after",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
    }
    return {key: value for key, value in headers.items() if key in keep}


def _atomic_text(path: Path, content: str) -> None:
    _atomic_bytes(path, content.encode("utf-8"))


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
