from __future__ import annotations

from typing import Any

from pydantic import HttpUrl

from model_intelligence.collectors.common import collect_json_source
from model_intelligence.contracts import SourceKind, SourceSpec
from model_intelligence.http import ConditionalHttpClient
from model_intelligence.snapshots import SnapshotOutcome, SnapshotStore

SOURCE = SourceSpec(
    key="models-dev.catalog",
    kind=SourceKind.API,
    url=HttpUrl("https://models.dev/api.json"),
    canonical=False,
    expected_content_type="application/json",
)


async def collect(
    client: ConditionalHttpClient,
    store: SnapshotStore,
) -> SnapshotOutcome:
    return await collect_json_source(
        source=SOURCE,
        client=client,
        store=store,
        validate=_validate,
    )


def _validate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        raise ValueError("expected non-empty provider object")

    providers = 0
    models = 0
    for provider_id, provider in payload.items():
        if not isinstance(provider_id, str) or not isinstance(provider, dict):
            raise ValueError("provider entries must be keyed objects")
        providers += 1
        provider_models = provider.get("models", {})
        if not isinstance(provider_models, dict):
            raise ValueError(f"provider {provider_id!r} has non-object models field")
        models += len(provider_models)

    if providers < 1 or models < 1:
        raise ValueError("catalog contains no providers or models")
    return {"provider_count": providers, "model_count": models}
