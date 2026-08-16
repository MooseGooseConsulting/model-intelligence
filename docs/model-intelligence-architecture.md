# Model Intelligence Collector Architecture

* **Arena’s official dataset is event-driven, not guaranteed daily.** Arena’s maintainer says it is updated “each day we do a leaderboard update.” The `latest` split is the newest published board; `full` preserves the historical sequence, including `leaderboard_publish_date`. ([Hugging Face][1])
* **I think we should build one durable “model intelligence” backend now.** Plain Python collectors + immutable snapshots + DuckDB/Parquet is enough; agents are unnecessary for the core pipeline.
* The backend should cover **model metadata, product availability, pricing, provider performance, public benchmarks, coding-agent benchmarks, Arena, local inference artifacts, runtime compatibility, and our own hardware measurements**—with model/harness/effort/version kept distinct.
* **📌 Explicit reuse note:** before implementing Arena, grab `oolong-tea-2026/arena-ai-leaderboards` **and** `KTibow/brokierouter`'s Arena→OpenRouter identity mapping. Do not rebuild those pieces from zero.

## First: how fresh is Arena really?

The exact answer from Arena is:

> the dataset is updated **on each day Arena publishes a leaderboard update**. ([Hugging Face][1])

So I would **not** model it as:

```text
Arena updates every 24 hours
```

I'd model it as:

```text
Arena publishes board revision
          ↓
HF leaderboard-dataset changes
          ↓
our collector sees new source revision
          ↓
ingest new observations
```

Arena deliberately provides two temporal views:

```text
latest = current published leaderboard
full   = every historical published leaderboard
```

and includes a publish date so we know which observation belongs to which leaderboard release. ([Arena AI][2])

### What I would do

Poll the HF dataset **hourly**, but do almost no work unless its revision/ETag changes. That gives us near-current data without pretending the underlying leaderboard itself refreshes hourly.

Then separately run our **Arena live-page enrichment** every ~6 hours. Arena's live UI contains things the published dataset doesn't necessarily capture—price, max context, rank spread and other presentation fields; Arena itself documents those optional leaderboard columns. ([Arena AI][3])

---

# What you actually keep asking me to know

Looking back over our model-selection/model-dashboard discussions, this is substantially larger than “a benchmark database.” You repeatedly end up wanting to answer some variation of:

**What is the model? How good is it? How good is it specifically at coding/agents? At what reasoning effort? Through what harness? What does it cost? How fast is it? How much context does it really get in this product? Can I run it locally? Which quant? On which runtime? Does MTP work? What does it fit on? And how has all of that changed over time?**

I would make these the canonical source families:

| Information we want                                                                                                      | Proper primary source                                                                                                                                                                                                                                                 | Collector strategy                                     |
| ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Canonical model identity**, aliases, provider, release/lifecycle, modalities, basic capabilities, context              | **models.dev** as the broad baseline registry; first-party lab metadata overrides when necessary. models.dev exposes its database through `api.json`. ([GitHub][4])                                                                                                   | API snapshot                                           |
| **OpenRouter catalog**, context, modalities, supported parameters, pricing                                               | OpenRouter `/api/v1/models`. ([OpenRouter][5])                                                                                                                                                                                                                        | API                                                    |
| **OpenRouter provider availability**, provider-specific price, quantization, endpoint context, throughput/latency/uptime | Per-model OpenRouter `/endpoints`. ([OpenRouter][6])                                                                                                                                                                                                                  | API; frequent for models we care about                 |
| **Actual OpenRouter popularity**                                                                                         | `/datasets/rankings-daily`; top-50 model token traffic + history. ([OpenRouter][7])                                                                                                                                                                                   | API/history                                            |
| **What models people use for coding/search/etc.**                                                                        | `/classifications/task`, including model share within task classes. ([OpenRouter][8])                                                                                                                                                                                 | API                                                    |
| **OpenRouter/AA/Design Arena benchmark feed**                                                                            | OpenRouter `/benchmarks`. ([OpenRouter][9])                                                                                                                                                                                                                           | API                                                    |
| **Independent model quality + API speed/latency/pricing**                                                                | **Artificial Analysis Data API**. It explicitly exposes benchmarks, pricing, latency, throughput, availability and model metadata. ([Artificial Analysis][10])                                                                                                        | API                                                    |
| **Arena human preference scores**, categories, votes, CI, history                                                        | Official `lmarena-ai/leaderboard-dataset`, `latest` + `full`. ([Arena AI][2])                                                                                                                                                                                         | HF dataset                                             |
| **Arena live-only enrichment**                                                                                           | `arena.ai/leaderboard/...`                                                                                                                                                                                                                                            | Deterministic scrape; reuse oolong collector framework |
| **CursorBench** score/cost/tokens/steps + effort variants                                                                | **Cursor `/evals`**. Current board is CursorBench **3.2**, introduced July 8, 2026. ([Cursor][11])                                                                                                                                                                    | First-party page snapshot/parser                       |
| **Cursor model availability, product-specific context, prices, Max/Fast/effort modes, promos**                           | Cursor's **Models & Pricing** data; Cursor's pricing policy explicitly identifies that page as the canonical pricing publication. ([Cursor][12])                                                                                                                      | First-party page parser                                |
| **GitHub Copilot model availability / product behavior / costs**                                                         | GitHub's Copilot model comparison + **Models and pricing** docs. GitHub shifted most Copilot billing to usage-based billing on June 1, 2026; legacy annual plans need a separate billing record because their old multipliers still apply. ([GitHub Docs][13])        | First-party docs parser                                |
| **SWE-bench Verified etc.**                                                                                              | `SWE-bench/swe-bench.github.io`; the site's own repo stores leaderboard data as structured JSON. ([GitHub][14])                                                                                                                                                       | GitHub JSON, no HTML scraping                          |
| **SWE-bench Pro**                                                                                                        | Scale's official `SWE-bench_Pro-os` repo + HF dataset + official leaderboard. The repo is still being updated in 2026, including leaderboard corrections. ([GitHub][15])                                                                                              | Git/HF                                                 |
| **Terminal-Bench**                                                                                                       | Current **Terminal-Bench 2.1** repo/Harbor leaderboard. ([GitHub][16])                                                                                                                                                                                                | GitHub/Harbor                                          |
| **Aider Polyglot**                                                                                                       | Aider's own leaderboard. It includes score, run cost, command/edit format and related run details; its published price is explicitly the price **when that run occurred**, which is exactly why we must separate benchmark cost from current API price. ([Aider][17]) | Page/repo parser                                       |
| **Exact local weights / quant files / revisions / config / model cards**                                                 | Hugging Face Hub API. `HfApi` gives model/repo/file metadata, and HF supports webhooks for repository changes. ([Hugging Face][18])                                                                                                                                   | HF API + webhook                                       |
| **Runtime compatibility** — llama.cpp, vLLM, SGLang, MLX, ExLlama, etc.                                                  | Each runtime's official GitHub releases/issues/code                                                                                                                                                                                                                   | GitHub adapter                                         |
| **Real local performance** — quant × context × KV format × MTP × hardware × runtime                                      | **Our own benchmark results**, not an aggregator                                                                                                                                                                                                                      | Benchmark runner → same warehouse                      |

That last row is important. Practitioner discussion still reflects a real hole: public leaderboards usually compare base model quality, **not whether Q4/Q6/Q8 preserves tool calling, structured output or long-context behavior on a particular runtime**. Recent LocalLLaMA discussion specifically calls out the lack of useful task-level quantized-model evaluations. ([Reddit][19])

So public data cannot replace your own 5090 / Strix Halo / multi-GPU measurements there.

---

## And I'd support the other coding benchmarks as plug-ins, not bake them into the schema

You've repeatedly wanted things beyond the obvious five: **DeepSWE, FrontierCode, Senior SWE-bench, SWE-Atlas-QnA, Vals, Vibe Code, code-migration benchmarks, MCP/tool-use benchmarks, BFCL/Tau-style agent/tool evals, long-horizon tests, etc.**

The schema should therefore never contain fields like:

```text
cursorbench_score
swebench_score
terminalbench_score
```

That's how this turns into garbage six months later.

Instead:

```text
benchmark
benchmark_version
benchmark_variant
task_family

model
model_revision
reasoning_effort

agent_harness
harness_version

provider
endpoint

score
score_lower_ci
score_upper_ci

cost
input_tokens
output_tokens
cached_tokens
steps

run_date
source_published_at
source_url
source_revision
```

Then:

```text
CursorBench / 3.2 / overall
GPT-5.6 Sol / Max
Cursor Agent / <harness rev>
67.2%
$5.69/task
...
```

is a **different observation** from CursorBench 3.1.

This matters immediately: Cursor changed the benchmark on July 8 from 3.1 to **3.2**, adding instruction-following and advanced tool-use problems. Scores across the version boundary should not silently appear in one time series. ([Cursor][11])

Same thing for SWE-bench:

**model != agent system**.

A model running in OpenHands, SWE-agent, Codex, Cursor, Pi, Claude Code, etc. is a system result, not a naked model result.

---

# The backend I would build

No Kafka. No agent orchestration. No LLM repeatedly trying to understand webpages.

### 1. Immutable raw layer

Every fetch is retained exactly.

```text
data/
  raw/
    arena/
    cursor/
    openrouter/
    artificial-analysis/
    swebench/
    swebench-pro/
    terminal-bench/
    aider/
    models-dev/
    huggingface/
```

Each observation gets:

```text
fetched_at
source_as_of
source_revision
http_etag
content_hash
collector_version
```

If the response hasn't changed, **don't create another full blob**.

---

### 2. Typed adapters

Something like:

```text
collectors/
  arena_hf.py
  arena_live.py

  openrouter_models.py
  openrouter_endpoints.py
  openrouter_usage.py
  openrouter_tasks.py
  openrouter_benchmarks.py

  artificial_analysis.py

  cursor_models.py
  cursorbench.py
  github_copilot.py

  swebench.py
  swebench_pro.py
  terminal_bench.py
  aider.py

  models_dev.py
  huggingface.py
```

Python + `httpx` + Pydantic is perfectly sufficient.

For OpenRouter specifically, I'd now use the **official OpenRouter Python SDK** rather than hand-maintain every endpoint wrapper; the official SDK is stable at v1.0. ([GitHub][20])

---

# 3. One identity layer

This is probably the most annoying part of the system.

We need:

```text
canonical_model
canonical_variant
source_alias
```

For example:

```text
canonical model
    anthropic/claude-opus-5

aliases
    Cursor: Opus 5
    Arena: claude-opus-5-high
    OpenRouter: anthropic/claude-opus-5
    AA: <AA stable id>

variant
    reasoning_effort = high
```

And **never destroy the original source name**.

This is exactly why I want to steal `KTibow/brokierouter`'s Arena→OpenRouter mapping rather than spend another afternoon rebuilding hundreds of aliases.

---

# 4. DuckDB + Parquet analytical core

I would use approximately these durable tables:

```text
models
model_aliases
model_variants

product_availability
provider_endpoints
pricing_observations
endpoint_performance

benchmark_definitions
benchmark_runs

arena_ratings
usage_rankings
task_market_share

hf_repositories
model_artifacts
runtime_support

local_benchmark_runs

source_snapshots
ingest_runs
```

For a single-user analytical application, **DuckDB + Parquet is a much better starting point than standing up a database service just because databases exist**.

If the frontend eventually needs high write concurrency or multi-user transactional features, we can serve selected current-state tables from Postgres. The historical corpus can remain Parquet.

---

# 5. Refresh cadence I'd actually use

| Collector                                    | Check cadence |                Full ingestion |
| -------------------------------------------- | ------------: | ----------------------------: |
| Arena official HF dataset                    |    **Hourly** | only when HF revision changes |
| Arena live enrichment                        |       6 hours |                changed boards |
| CursorBench                                  |       6 hours |        only when hash changes |
| Cursor model/pricing                         |     3–6 hours |                     on change |
| OpenRouter models                            |        1 hour |                     on change |
| OpenRouter endpoints, **frontier/watchlist** |     30–60 min |                   each sample |
| OpenRouter endpoints, entire catalog         |         Daily |                    full sweep |
| OpenRouter rankings/tasks/apps               |         Daily |                        append |
| Artificial Analysis                          |    6–24 hours |   append changed observations |
| models.dev                                   |       6 hours |              on revision/hash |
| SWE-bench / Pro                              |         Daily |          on Git commit change |
| Terminal-Bench                               |         Daily |                     on change |
| Aider                                        |         Daily |                     on change |
| watched HF model/org repos                   |       webhook |                   immediately |
| general HF discovery                         |         Daily |                          diff |

So it behaves **fast where the information actually moves fast**, without hammering static leaderboards.

---

# 6. Then your frontend becomes substantially richer than any one of these sites

The API can expose views such as:

```text
/models
/models/:id

/models/:id/pricing-history
/models/:id/provider-performance
/models/:id/benchmarks
/models/:id/arena-history
/models/:id/product-availability
/models/:id/local-artifacts
/models/:id/local-performance

/benchmarks/:benchmark
/products/cursor
/products/copilot
/providers
/releases
/changes
```

And then the UI can answer the questions you repeatedly end up having me manually research:

**Quality**

```text
AA Intelligence
AA Coding
AA Agentic
Arena overall
Arena coding
CursorBench
SWE-bench Verified
SWE-bench Pro
Terminal-Bench
Aider
...
```

**Economics**

```text
input $
cache-read $
cache-write $
output $
cost/task
cost/successful-task
```

**Speed**

```text
provider
TTFT
output tok/s
end-to-end
uptime
```

**Agent suitability**

```text
tools
structured output
reasoning levels
benchmark harness
steps
tool-use benchmarks
long-horizon benchmarks
```

**Local**

```text
weights
total/active params
quant
exact file
VRAM/RAM
context
KV quant
MTP/spec decode
runtime support

prefill tok/s
decode tok/s
TTFT
memory use
quality delta
tool-call success
```

That's essentially the data model you've been converging on in all of these separate conversations.

---

## 📌 The code-reuse note I would put at the top of the implementation issue

**Do these before writing the Arena collector:**

1. **Fork/clone `oolong-tea-2026/arena-ai-leaderboards`.** Reuse its leaderboard discovery, dated snapshots, schema validation, retry/failure handling and GitHub Actions structure. Its current collector already does the machinery we need.
2. **Grab `KTibow/brokierouter/scripts/fetch_arena.py`'s model crosswalk.**
3. Change the Arena architecture so **official HF `leaderboard-dataset` is canonical for scores/history**.
4. Reduce the live scraper to **enrichment + drift detection**, rather than asking an LLM to reconstruct data Arena already publishes.
5. Preserve the oolong raw snapshot format so if Arena changes its site we have evidence of exactly what broke.

That is the architecture I would choose. **Probably 80–90% of this backend is boring deterministic ETL, which is a feature.** LLM/agent work should come later for things like discovering a brand-new source or proposing uncertain aliases—not sit in the critical data path.

I reviewed current sources through **August 16, 2026**: recent Reddit/LocalLLaMA discussion for practitioner gaps, current GitHub implementations for reusable collectors, and first-party Arena, Cursor, OpenRouter, Artificial Analysis, GitHub, Hugging Face, SWE-bench, Terminal-Bench and Aider sources to define the actual ingestion contracts.

[1]: https://huggingface.co/spaces/lmarena-ai/arena-leaderboard/discussions/86?utm_source=chatgpt.com "lmarena-ai/arena-leaderboard · add a button to download the results in the tables"
[2]: https://arena.ai/blog/arena-leaderboard-dataset/?utm_source=chatgpt.com "Arena Leaderboard Dataset"
[3]: https://arena.ai/blog/march-2026-arena-updates?utm_source=chatgpt.com "March 2026: Arena Updates across Product, Leaderboard Rankings & Research - Arena.ai"
[4]: https://github.com/anomalyco/models.dev?utm_source=chatgpt.com "GitHub - anomalyco/models.dev: An open-source database of AI models. · GitHub"
[5]: https://openrouter.ai/docs/api/api-reference/models/get-models?utm_source=chatgpt.com "List all models and their properties | OpenRouter | Documentation"
[6]: https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints?utm_source=chatgpt.com "List all endpoints for a model | OpenRouter | Documentation"
[7]: https://openrouter.ai/docs/api/api-reference/datasets/get-rankings-daily?utm_source=chatgpt.com "Daily token totals for top 50 models | OpenRouter | Documentation"
[8]: https://openrouter.ai/docs/api/api-reference/classifications/get-task-classifications?utm_source=chatgpt.com "Task classification market share | OpenRouter | Documentation"
[9]: https://openrouter.ai/docs/api/api-reference/benchmarks/get-benchmarks?utm_source=chatgpt.com "List Benchmarks | OpenRouter | Documentation"
[10]: https://artificialanalysis.ai/data-api?utm_source=chatgpt.com "AI Model Data API | Artificial Analysis"
[11]: https://cursor.com/evals?utm_source=chatgpt.com "Cursor · CursorBench"
[12]: https://cursor.com/terms/pricing?utm_source=chatgpt.com "Cursor · Pricing Policy"
[13]: https://docs.github.com/en/copilot/reference/ai-models/model-comparison?search-overlay-input=agents&search-overlay-open=true&utm_source=chatgpt.com "AI model comparison - GitHub Docs"
[14]: https://github.com/swe-bench/swe-bench.github.io?utm_source=chatgpt.com "GitHub - SWE-bench/swe-bench.github.io: Landing page + leaderboard for SWE-Bench benchmark · GitHub"
[15]: https://github.com/scaleapi/SWE-bench_Pro-os?utm_source=chatgpt.com "GitHub - scaleapi/SWE-bench_Pro-os: SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks? · GitHub"
[16]: https://github.com/harbor-framework/terminal-bench-2-1?utm_source=chatgpt.com "GitHub - harbor-framework/terminal-bench-2-1: Terminal-Bench 2.1 · GitHub"
[17]: https://aider.chat/docs/leaderboards/?utm_source=chatgpt.com "Aider LLM Leaderboards | aider"
[18]: https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_api?utm_source=chatgpt.com "HfApi Client · Hugging Face"
[19]: https://www.reddit.com/r/LocalLLaMA/comments/1uc9aw3/leaderboard_for_quantized_models_similar_to/?utm_source=chatgpt.com "Leaderboard for quantized models, similar to artificial analysis?"
[20]: https://github.com/OpenRouterTeam/python-sdk?utm_source=chatgpt.com "GitHub - OpenRouterTeam/python-sdk · GitHub"
