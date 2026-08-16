from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from model_intelligence.contracts import SourceKind, SourceSpec
from model_intelligence.http import HttpFetch
from model_intelligence.snapshots import SnapshotStore

SOURCE = SourceSpec(
    key="test.source",
    kind=SourceKind.API,
    url="https://example.com/data.json",
    expected_content_type="application/json",
)


def _fetch(body: bytes | None, *, status: int = 200, etag: str = '"v1"') -> HttpFetch:
    return HttpFetch(
        url="https://example.com/data.json",
        fetched_at=datetime(2026, 8, 16, 7, 0, tzinfo=timezone.utc),
        status_code=status,
        headers={"content-type": "application/json", "etag": etag},
        body=body,
    )


def test_content_addressed_snapshot_and_same_body_do_not_duplicate(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)

    first = store.persist(SOURCE, _fetch(b'{"ok":true}'))
    second = store.persist(SOURCE, _fetch(b'{"ok":true}', etag='"v2"'))

    assert first.changed is True
    assert first.body_path is not None and first.body_path.exists()
    assert first.metadata_path is not None and first.metadata_path.exists()
    assert second.changed is False
    assert second.body_path == first.body_path
    assert second.metadata_path is None
    assert store.read_state(SOURCE.key).etag == '"v2"'  # type: ignore[union-attr]


def test_304_advances_last_checked_only(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    store.persist(SOURCE, _fetch(b'{"ok":true}'))
    before = store.read_state(SOURCE.key)
    assert before is not None

    later = _fetch(None, status=304)
    later = HttpFetch(
        url=later.url,
        fetched_at=later.fetched_at + timedelta(hours=1),
        status_code=later.status_code,
        headers=later.headers,
        body=None,
    )
    result = store.persist(SOURCE, later)
    after = store.read_state(SOURCE.key)

    assert result.not_modified is True
    assert after is not None
    assert after.latest_body_sha256 == before.latest_body_sha256
    assert after.last_checked_at > before.last_checked_at


def test_quarantine_never_replaces_accepted_state(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    store.persist(SOURCE, _fetch(b'{"ok":true}', etag='"good"'))
    accepted = store.read_state(SOURCE.key)
    assert accepted is not None

    body_path, metadata_path = store.quarantine(
        SOURCE,
        _fetch(b"<html>upstream error</html>", etag='"bad"'),
        reason="expected JSON",
    )
    after = store.read_state(SOURCE.key)

    assert body_path.exists()
    assert metadata_path.exists()
    assert after == accepted
