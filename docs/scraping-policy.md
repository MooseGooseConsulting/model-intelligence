# Durable Source Collection Policy

The collector stack is **structured-source first**. Browser automation is an escalation path, not the default.

The objective is not merely to make a page scrape succeed today. The objective is to detect source changes, preserve evidence, fail observably, and make a broken parser cheap to repair without corrupting historical data.

## Acquisition ladder

Use the first viable level and do not escalate merely because a browser tool exists.

### Level 0 — official structured source

Prefer, in order:

1. documented first-party API;
2. official dataset / Parquet / CSV / JSON publication;
3. official Git repository or release artifact;
4. first-party machine-readable embedded data.

Examples:

- Arena scores/history: official Hugging Face leaderboard dataset, not the rendered Arena table.
- OpenRouter catalog/usage/benchmarks: documented OpenRouter APIs.
- SWE-bench data: published repository/dataset artifacts where available.

### Level 1 — direct HTTP

For public HTTP resources use the shared `ConditionalHttpClient`:

- one pooled `httpx.AsyncClient`;
- HTTP/2 when negotiated;
- explicit timeouts;
- bounded retry set;
- exponential backoff + jitter;
- `Retry-After` support;
- `ETag` / `If-None-Match`;
- `Last-Modified` / `If-Modified-Since`;
- stable descriptive user agent;
- source-specific concurrency/rate limits.

A 200 response is not success until the source validator accepts it.

### Level 2 — deterministic HTML parsing

Use this only when the desired information exists in server-rendered HTML but no better structured source exists.

Parser rules:

- prefer semantic labels/headings/table headers over positional CSS selectors;
- parse embedded JSON/JSON-LD when it is the page's own data payload;
- assert invariants such as expected columns, unique IDs, row-count floors, units, and value domains;
- retain the raw HTML snapshot before normalization;
- schema drift must raise, not silently return an empty table.

### Level 3 — browser-assisted network discovery

For JavaScript applications, prefer the application's public data response over its rendered DOM when feasible.

Use Playwright to inspect `fetch`/XHR responses and determine whether the page is backed by a stable public JSON/GraphQL/data endpoint. Once identified and appropriate to use, move normal collection back to a typed HTTP collector.

This is usually more durable than extracting text from virtualized tables.

### Level 4 — browser DOM collection

Use Crawlee + Playwright when the data genuinely exists only after browser execution or interaction.

Default browser stack:

- `crawlee[playwright]` for request queues, sessions, retries, concurrency and browser lifecycle;
- `PlaywrightCrawler` for known JS-only sources;
- `AdaptivePlaywrightCrawler` only when HTTP/browser fallback is useful and its behavior is well tested for the source;
- source-specific parsers and invariants remain mandatory.

Browser collectors should capture enough diagnostics on failure to reproduce the source state: URL, timestamp, HTML/snapshot where allowed, relevant response metadata, and parser error. Screenshots are useful diagnostics but are not the canonical data representation.

### Level 5 — assisted repair, never silent authority

LLMs, adaptive selector recovery, or selector-healing systems may help:

- diagnose a changed page;
- propose a new parser;
- compare old/new DOM structures;
- extract a candidate fixture for human/test review.

They must **not silently promote repaired data into the authoritative warehouse** without deterministic validation. A source drift event should create a visible failure/quarantine record, not a plausible-looking wrong dataset.

## Promotion semantics

Every collector follows:

```text
fetch
  ↓
retain transport evidence
  ↓
parse
  ↓
validate source invariants/schema
  ├── invalid → quarantine; do NOT advance checkpoint
  └── valid
       ↓
content hash
       ↓
immutable raw snapshot (if changed)
       ↓
advance source checkpoint
       ↓
normalize / publish read models
```

The last known-good observation remains queryable when a new source response fails validation.

## Snapshot requirements

Accepted source observations record at minimum:

- source key and source URL;
- fetch timestamp;
- source-provided `as_of`/publication time when available;
- ETag / Last-Modified when available;
- SHA-256 of raw body;
- collector version;
- source schema version;
- selected rate/cache headers;
- source-specific validation facts such as row/model counts.

Raw bodies are content-addressed. Re-fetching identical bytes does not create another full body copy.

## Source contracts

Every source adapter should document:

- authority: canonical vs enrichment;
- source URL/API/dataset;
- refresh/check cadence;
- expected media/schema shape;
- stable identity fields;
- invariants and minimum cardinality;
- rate-limit behavior;
- historical/backfill mechanism;
- failure semantics;
- whether browser execution is required;
- license/attribution requirements for redistributed data/code.

## Anti-patterns

Do not:

- scrape HTML when the publisher exposes the same data as JSON/Parquet/API;
- use an LLM as the routine table parser;
- write normalized rows before retaining/verifying raw evidence;
- treat HTTP 200 as sufficient validation;
- advance ETag/hash state on invalid content;
- overwrite historical observations in place;
- rely only on a model display name as identity;
- hard-code benchmark names as database columns;
- let a scraper failure break the website build/deploy;
- bypass authentication, access controls, or deliberate anti-abuse restrictions.

## Tooling baseline

The initial stack is intentionally small:

- **HTTP / APIs:** `httpx` async client;
- **validation/contracts:** Pydantic;
- **browser escalation:** Crawlee Python + Playwright;
- **analytical external-data layer:** DuckDB + Parquet;
- **testing:** pytest, source fixtures and invariant tests;
- **CLI:** Typer;
- **scheduling:** deployment concern; collectors remain runnable as ordinary idempotent commands.

Add a specialized scraping framework only for a demonstrated source failure mode. Do not turn the ingestion layer into a collection of overlapping crawler abstractions.
