from __future__ import annotations

import pytest

from model_intelligence.collectors.arena import _validate_manifest
from model_intelligence.collectors.models_dev import _validate as validate_models_dev
from model_intelligence.collectors.openrouter import _validate_models


def test_openrouter_requires_unique_model_ids() -> None:
    payload = {
        "data": [
            {"id": "vendor/model", "pricing": {}},
            {"id": "vendor/model", "pricing": {}},
        ]
    }
    with pytest.raises(ValueError, match="duplicate model id"):
        _validate_models(payload)


def test_models_dev_requires_nested_models_object() -> None:
    with pytest.raises(ValueError, match="non-object models field"):
        validate_models_dev({"provider": {"models": []}})


def test_arena_manifest_requires_text_history_and_style_control() -> None:
    required = [
        ("text", "latest"),
        ("text", "full"),
        ("text_style_control", "latest"),
        ("text_style_control", "full"),
    ]
    payload = {
        "parquet_files": [
            {
                "config": config,
                "split": split,
                "url": f"https://example.com/{config}-{split}.parquet",
                "size": 123,
            }
            for config, split in required
        ]
    }
    facts = _validate_manifest(payload)
    assert facts["parquet_file_count"] == 4
    assert facts["table_count"] == 4

    payload["parquet_files"].pop()
    with pytest.raises(ValueError, match="Arena text tables missing"):
        _validate_manifest(payload)
