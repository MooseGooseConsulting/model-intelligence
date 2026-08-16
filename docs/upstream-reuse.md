# Upstream Reuse Register

Do not reimplement known-good collector mechanics or identity research without first checking the upstream projects below.

This file records **what to reuse conceptually or directly, why, and any licensing constraint** before code is copied.

## Arena daily snapshot framework

Repository: `oolong-tea-2026/arena-ai-leaderboards`

Useful pieces:

- automatic leaderboard discovery;
- dated snapshot layout and `latest.json` pointer;
- JSON Schema validation;
- retry/failure behavior;
- GitHub Actions scheduling pattern;
- special handling for the Agent leaderboard's multi-dimensional score shape.

The project is MIT-licensed. Its current collector uses Jina Reader plus LLM extraction from rendered Arena pages. We should **reuse the surrounding mechanics, not preserve LLM extraction as the preferred data path**. Official Arena/Hugging Face data is canonical for ratings/history; browser/page extraction is an enrichment fallback.

Before adapting code, pin the upstream commit and preserve license attribution in the resulting source file or NOTICE as appropriate.

## Arena ↔ OpenRouter identity research

Repository: `KTibow/brokierouter`

File of interest: `scripts/fetch_arena.py`

Useful piece:

- a large maintained Arena model-name → OpenRouter model-ID mapping that distinguishes direct vs reasoning/thinking variants.

This mapping is valuable prior research, but the repository currently exposes no root `LICENSE` file. **Do not copy the mapping wholesale until reuse permission/license is established.** It may be used as a research/reference source to independently derive and test our own alias table, retaining provenance for each mapping decision.

The identity layer must eventually support multiple evidence sources and confidence/state, rather than one hard-coded dictionary becoming unquestioned truth.

## `reyamira/models`

Useful pieces:

- normalization of multiple benchmark sources;
- consuming the oolong Arena snapshots;
- merging Arena boards into model-level metrics;
- a mature CLI/TUI schema for model and benchmark comparison.

Use it primarily as schema/UI/normalization prior art. `model-intelligence` needs a more history-preserving source-observation model than a current-state browser.

## OpenRouter clients and pipelines

### `OpenRouterTeam/python-sdk`

Prefer the official SDK for documented OpenRouter API coverage when it reduces hand-maintained request/response code. Keep raw HTTP snapshots at the source boundary when we need exact response evidence; the SDK does not replace provenance storage.

### `realmorrisliu/openrouter-rs`

Useful as implementation/schema research for newer OpenRouter discovery, endpoint telemetry, rankings, classifications, and benchmark response shapes.

### `ronniechong/ai-pulse-data`

Useful pipeline patterns:

- fetch → validate → normalize → diff → publish;
- date-window backfill;
- rolling history repair;
- scheduled GitHub Actions ingestion.

## Rule

For every external project considered for direct code reuse:

1. record repository + exact commit;
2. verify license before copying;
3. copy the smallest useful unit, not the whole architecture;
4. preserve attribution/license requirements;
5. wrap it in our source contract and invariant tests;
6. do not inherit a less-authoritative acquisition method when a better primary source now exists.
