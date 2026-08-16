# Repository Boundaries

This repository owns **external model intelligence**: durable observations about models, providers, products, public benchmarks, availability, pricing, public performance telemetry, model artifacts, and source identity over time.

It does not own every place that model-related facts originate or every place they are displayed.

## Decision

| Repository / system | Owns | Does not own |
|---|---|---|
| `MooseGooseConsulting/model-intelligence` | External/public source collectors; immutable source evidence; source schemas; model/provider/product identity resolution; historical external observations; normalized external-intelligence exports | Website presentation; local inference experiment execution; production database lifecycle; private UI annotations |
| `MooseGooseConsulting/LocalLargeLanguageModels` | Local serving/evaluation execution; run recipes; hardware/runtime evidence; canonical quantitative local measurements in its `llm-measurements` store | Global public model catalog; Cursor/OpenRouter/Arena scraping; public benchmark history warehouse |
| `MooseGooseConsulting/MooseGooseWebsite` | Compass and Observatory product surfaces; app-specific read models; private annotations/favorites/current picks; authorization; UI caching/projections | Crawling upstream model sources; canonical public benchmark history; raw source evidence |
| Infrastructure control plane | Database/object-store lifecycle, credentials, backup, topology, schedules where deployed | Domain semantics of model intelligence |

## Why the collectors do not live in MooseGooseWebsite

The website already has the right product split:

- **Compass** is the catalog: models as things in the world.
- **Observatory** is the deployment ledger: models as they exist on owned hardware/runtime paths.

Putting upstream collectors inside the Next.js repository would conflate three concerns:

1. source acquisition and historical evidence;
2. canonical normalization and identity resolution;
3. presentation and private application behavior.

It would also couple collection cadence and Python/data dependencies to the web deployment lifecycle. A broken Cursor or Arena parser should not be able to break a website build, and a website refactor should not rewrite ingestion history.

The website should consume a **versioned read contract** published by this repository. Initially that can be generated JSON/Parquet plus a manifest; later it can be a thin query service or a Postgres projection if the UI needs lower-latency filtered reads.

## Public intelligence vs. local measurements

`LocalLargeLanguageModels` already defines `llm-measurements` Postgres as the canonical detail store for owned benchmark/evaluation runs. That contract remains authoritative.

`model-intelligence` should therefore treat local results as a separate source family:

```text
LocalLargeLanguageModels
       │
       ├── runs / artifacts / measurements
       │          canonical there
       ▼
versioned export or read adapter
       │
       ▼
model-intelligence identity join
       │
       ▼
Compass / Observatory read model
```

Do not make a second mutable copy of local measurements authoritative. If this repository materializes local rows for analytics, record their upstream stable IDs, source revision/time, and import timestamp so they remain a cache/projection of the source store.

## Identity boundary

This repository should own the cross-source identity map because neither a website nor a local benchmark runner has enough scope to do it reliably.

Examples:

```text
canonical model       anthropic/claude-opus-5
Arena alias            claude-opus-5-high
OpenRouter alias       anthropic/claude-opus-5
Cursor display name    Opus 5
local artifact alias   <publisher/repository/revision>
variant                reasoning_effort=high
```

Every observation retains its **original source identifier and display name**. Canonical IDs are join keys, not replacements for source evidence.

## Website integration target

The first integration should replace the current static Compass seed with a generated, versioned catalog read model while preserving application-only fields separately.

Suggested split:

```text
model-intelligence export
  model identity
  provider / release / modalities
  public context limits
  public pricing
  benchmark observations
  source freshness
  external availability

MooseGooseWebsite-owned annotations
  favorite
  current pick
  private notes
  UI grouping/preferences

LocalLargeLanguageModels / Observatory
  local quant
  runtime/backend
  hardware
  achieved context
  measured speed
  deployment status
  local evidence
```

This keeps Compass rich without making the web app the crawler or the local serving repo the public-data warehouse.
