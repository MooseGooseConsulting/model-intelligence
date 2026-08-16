from __future__ import annotations

from typing import Any

from model_intelligence.collectors.common import collect_json_source
from model_intelligence.contracts import SourceKind, SourceSpec
from model_intelligence.http import ConditionalHttpClient
from model_intelligence.snapshots import SnapshotOutcome, SnapshotStore

PARQUET_MANIFEST_SOURCE = SourceSpec(
    key="arena.leaderboard-dataset.parquet-manifest",
    kind=SourceKind.DATASET,
    url=(
        "https://datasets-server.huggingface.co/parquet"
        "?dataset=lmarena-ai%2Fleaderboard-dataset"
    ),
    canonical=True,
    expected_content_type="application/json",
)

_REQUIRED_TEXT_TABLES = {
    ("text", "latest"),
    ("text", "full"),
    ("text_style_control", "latest"),
    ("text_style_control", "full"),
}


async def collect_manifest(
    client: ConditionalHttpClient,
    store: SnapshotStore,
) -> SnapshotOutcome:
    """Snapshot Arena's official HF Parquet manifest.

    The manifest gives us revision-sensitive, machine-readable URLs for the
    canonical dataset tables. Downloading and normalizing those Parquet files is
    intentionally a separate step so a manifest/schema failure cannot poison
    previously accepted leaderboard data.
    """

    return await collect_json_source(
        source=PARQUET_MANIFEST_SOURCE,
        client=client,
        store=store,
        validate=_validate_manifest,
    )


def _validate_manifest(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("expected top-level object")
    files = payload.get("parquet_files")
    if not isinstance(files, list) or not files:
        raise ValueError("missing parquet_files")

    tables: set[tuple[str, str]] = set()
    total_bytes = 0
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("parquet file entry must be an object")
        config = row.get("config")
        split = row.get("split")
        url = row.get("url")
        size = row.get("size")
        if not all(isinstance(value, str) and value for value in (config, split, url)):
            raise ValueError("parquet file entry missing config/split/url")
        if not isinstance(size, int) or size < 0:
            raise ValueError("parquet file entry has invalid size")
        tables.add((config, split))
        total_bytes += size

    missing = sorted(_REQUIRED_TEXT_TABLES - tables)
    if missing:
        raise ValueError(f"Arena text tables missing from manifest: {missing}")

    required_text_tables = sorted(
        f"{config}/{split}" for config, split in _REQUIRED_TEXT_TABLES
    )
    return {
        "parquet_file_count": len(files),
        "table_count": len(tables),
        "total_parquet_bytes": total_bytes,
        "required_text_tables": required_text_tables,
    }
