from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from model_intelligence.contracts import SourceSpec
from model_intelligence.http import ConditionalHttpClient
from model_intelligence.snapshots import SnapshotOutcome, SnapshotStore

JsonValidator = Callable[[Any], dict[str, Any]]


async def collect_json_source(
    *,
    source: SourceSpec,
    client: ConditionalHttpClient,
    store: SnapshotStore,
    validate: JsonValidator,
    headers: dict[str, str] | None = None,
) -> SnapshotOutcome:
    """Fetch, validate, then atomically promote one JSON source observation."""

    state = store.read_state(source.key)
    request_headers = {"Accept": "application/json"}
    request_headers.update(headers or {})
    fetch = await client.get(
        str(source.url),
        etag=state.etag if state else None,
        last_modified=state.last_modified if state else None,
        headers=request_headers,
    )

    if fetch.not_modified:
        return store.persist(source, fetch)

    if fetch.body is None:
        raise ValueError(f"{source.key} returned no response body")

    try:
        payload = json.loads(fetch.body)
        extra = validate(payload)
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        store.quarantine(source, fetch, reason=f"validation failed: {exc}")
        raise

    return store.persist(source, fetch, extra=extra)
