from __future__ import annotations

from typing import Any

from pydantic import HttpUrl

from model_intelligence.collectors.common import collect_json_source
from model_intelligence.contracts import SourceKind, SourceSpec
from model_intelligence.http import ConditionalHttpClient
from model_intelligence.snapshots import SnapshotOutcome, SnapshotStore

MODELS_SOURCE = SourceSpec(
    key="openrouter.models",
    kind=SourceKind.API,
    url=HttpUrl("https://openrouter.ai/api/v1/models?output_modalities=all"),
    canonical=True,
    expected_content_type="application/json",
)


async def collect_models(
    client: ConditionalHttpClient,
    store: SnapshotStore,
) -> SnapshotOutcome:
    return await collect_json_source(
        source=MODELS_SOURCE,
        client=client,
        store=store,
        validate=_validate_models,
    )


def _validate_models(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("expected top-level object")
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected non-empty data array")

    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("model rows must be objects")
        model_id = row.get("id")
        if not isinstance(model_id, str) or not model_id:
            raise ValueError("model row missing id")
        if model_id in seen:
            raise ValueError(f"duplicate model id {model_id!r}")
        seen.add(model_id)

        pricing = row.get("pricing")
        if pricing is not None and not isinstance(pricing, dict):
            raise ValueError(f"model {model_id!r} has invalid pricing")

    return {"model_count": len(rows)}
