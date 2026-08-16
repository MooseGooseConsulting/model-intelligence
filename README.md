# Model Intelligence

**Model Intelligence** is a planned, evidence-first data platform for tracking AI model identity, availability, pricing, provider performance, public evaluations, local-inference artifacts, runtime compatibility, and measured hardware performance over time.

> **Status: architecture phase.** This repository currently contains the initial design specification and source-contract research. It does **not** yet include production collectors, credentials, schedules, or a deployed warehouse.

## Design principles

The project is intended to make model selection answerable from durable, attributable observations rather than from stale point-in-time dashboards. Its core design uses deterministic source adapters, immutable raw snapshots, explicit model identity resolution, and an analytical layer based on DuckDB and Parquet.

The initial specification distinguishes between canonical primary sources, enrichment sources, and local measurements. It also keeps benchmark version, model revision, reasoning effort, agent harness, provider endpoint, and observed time as separate dimensions so historical comparisons remain meaningful.

## Initial architecture

The full source strategy, data model, refresh cadences, and reuse guidance are in [`docs/model-intelligence-architecture.md`](docs/model-intelligence-architecture.md).

| Area | Initial direction |
|---|---|
| Source adapters | Deterministic API, dataset, Git, and narrowly scoped page collectors |
| Raw layer | Immutable, content-addressed snapshots with source revision metadata |
| Identity | Canonical model identities plus explicit aliases and provider mappings |
| Analytics | DuckDB and Parquet for history-preserving queries |
| Local evidence | First-party runtime and hardware measurements stored separately from public leaderboards |

## Intended implementation sequence

The first executable work should establish the repository contracts and one well-bounded source adapter before broadening coverage. The architecture calls out the Arena source family as a suitable first vertical: use Arena’s official Hugging Face dataset for canonical scores and history, then limit live-page collection to enrichment and drift detection.

No automated task should be enabled until its source contract, rate behavior, raw-snapshot policy, and failure semantics are reviewed and documented.

## Contributing

This project is being established from an architecture specification. Before adding a collector, preserve source provenance, retain raw evidence, keep historical observations append-only, and avoid treating a rendered web page as canonical when an official structured source exists.
