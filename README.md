# Model Intelligence

**Model Intelligence** is an evidence-first data platform for tracking AI model identity, availability, pricing, provider performance, public evaluations, model artifacts, and source history over time.

> **Status: collector bootstrap.** The repository now has executable source contracts, conditional HTTP fetching, immutable content-addressed snapshots, quarantine semantics, and initial collectors for models.dev, OpenRouter, and Arena's official Hugging Face dataset manifest. A deployed scheduler/warehouse and website integration are still pending.

## Repository role

This repository owns **external/public model intelligence and cross-source identity resolution**. It is deliberately separate from:

- `MooseGooseWebsite`, which owns Compass/Observatory presentation and private application annotations;
- `LocalLargeLanguageModels`, which owns local serving/evaluation execution and its canonical local measurement store;
- infrastructure repositories, which own credentials, database/object-store lifecycle, schedules, backup, and deployment topology.

See [`docs/repository-boundaries.md`](docs/repository-boundaries.md).

## Collection philosophy

The stack is structured-source first:

1. official API/dataset/Git artifact;
2. direct conditional HTTP;
3. deterministic HTML parsing;
4. browser-assisted network discovery;
5. Crawlee + Playwright only for genuinely browser-only sources;
6. LLM/selector-healing assistance only for diagnosis/repair, never silent authoritative promotion.

Every accepted response is validated before it advances source state. Invalid 200-responses are quarantined and the previous known-good source checkpoint remains authoritative.

See [`docs/scraping-policy.md`](docs/scraping-policy.md).

## Current collectors

| Command | Source | Purpose |
|---|---|---|
| `model-intel collect models-dev` | `https://models.dev/api.json` | broad provider/model metadata snapshot |
| `model-intel collect openrouter-models` | OpenRouter `/api/v1/models?output_modalities=all` | canonical OpenRouter catalog/pricing/capabilities snapshot |
| `model-intel collect arena-manifest` | Hugging Face Dataset Viewer Parquet API | canonical manifest for Arena leaderboard dataset configs/splits |
| `model-intel collect bootstrap` | all three above | initial smoke/bootstrap collection |

## Development

Python 3.12+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

model-intel collect bootstrap
pytest
ruff check .
mypy
```

Browser dependencies are optional and should only be installed for collectors that actually require them:

```bash
pip install -e '.[scrape,dev]'
playwright install chromium
```

Runtime state defaults to `var/` and is intentionally ignored by Git:

```text
var/
  raw/          accepted immutable source bodies
  quarantine/   invalid/unaccepted source responses
  state/        small mutable last-known-good HTTP checkpoints
```

The production raw store can later move behind the same snapshot contract to S3-compatible object storage without making the website deployment responsible for ingestion.

## Design documents

- [`docs/model-intelligence-architecture.md`](docs/model-intelligence-architecture.md) — source map, data model, refresh cadences, long-term analytical design.
- [`docs/repository-boundaries.md`](docs/repository-boundaries.md) — ownership split across this repo, the website, local inference, and infrastructure.
- [`docs/scraping-policy.md`](docs/scraping-policy.md) — acquisition ladder, validation, browser escalation, and failure semantics.

## Next executable vertical

Arena is the first end-to-end target:

1. snapshot the official HF Parquet manifest;
2. fetch and schema-check `text` and `text_style_control` `latest`/`full` Parquet shards;
3. normalize historical rating observations while retaining source model names;
4. add the Arena↔canonical/OpenRouter identity crosswalk;
5. add narrowly scoped live-page enrichment for fields the official dataset does not publish;
6. publish a versioned read manifest usable by Compass.

Do not move routine upstream scraping into the Next.js app merely because Compass is where the data will ultimately be displayed.
