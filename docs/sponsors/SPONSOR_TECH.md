# Sponsor technology: Zetaris, Meterless and NVIDIA

This note explains how each sponsor technology is used in the PoE Reconciler and
where the evidence is. Each claim points to a file or a test in this repository.
All paths are relative to this file and exist on this branch, which includes the
runnable pipeline from PR #32 (merge order: see [Limitations](#7-limitations)).

| Sponsor | Role in the product | Code | Working feature | Test evidence |
| --- | --- | --- | --- | --- |
| Zetaris | Data layer: every run reads its ports through Zetaris SQL | [`zetaris.py`](../../backend/app/adapters/zetaris.py) | ZetarisAdapter, first step of every run | [`test_zetaris_adapter.py`](../../backend/tests/test_zetaris_adapter.py), `test_live_zone_through_real_zetaris` |
| Meterless H-MEM engine | Verification memory across runs | [`engines/hmem/`](../../backend/app/engines/hmem/), [`memory.py`](../../backend/app/agents/memory.py) | ResearchAgent reuses a previously verified official source during retries | [`test_hmem_conformance.py`](../../backend/tests/test_hmem_conformance.py), `test_research_uses_remembered_official_source` |
| Meterless Nightshift | Primary AI provider | [`generator.py`](../../backend/app/core/generator.py) | BriefingAgent writes the sailor-facing brief | [`test_generator.py`](../../backend/tests/test_generator.py), `test_live_brief_served_by_nemotron` |
| NVIDIA | Nemotron models served through Nightshift | same as Nightshift | The brief in the recorded live run | `test_live_nightshift_nemotron`, [`01_bermuda.live_nemotron.json`](../../output_examples/01_bermuda.live_nemotron.json) |

Tests named without a link are in
[`test_run_pipeline.py`](../../backend/tests/test_run_pipeline.py) or
[`test_generator.py`](../../backend/tests/test_generator.py).

## 1. Zetaris: data layer

The one-off administrator SQL registers the public
[`seed/ports_of_entry.geojson`](../../seed/ports_of_entry.geojson) snapshot as:

- Lightning database `BLUE_INTEL_REST`;
- REST table `BLUE_INTEL_REST.poe_seed`, pointed at the raw GitHub GeoJSON;
- schemastore container `blue_intel`; and
- view `blue_intel.poe_ports`, which explodes the GeoJSON `features` array into
  one row per port and projects identity, location, validation, source and
  coordinate fields.

The seed contains 1,169 features. The setup script refuses a verification count
other than 1,169. Evidence: [`zetaris_setup_poe.sql`](../../backend/scripts/zetaris_setup_poe.sql),
[`zetaris_setup.py`](../../backend/scripts/zetaris_setup.py).

At runtime, `ZetarisClient.get_ports(zone_name=None, mrgid=None, limit=500)` reads
`blue_intel.poe_ports` through the Zetaris SQL REST endpoint and converts rows to
the evaluator's port shape. Text filters are UTF-8 hex encoded before they enter
SQL; `mrgid` accepts integers only. The sample path reads 20 real rows copied
from the same seed. Evidence: [`zetaris.py`](../../backend/app/adapters/zetaris.py),
[`poe_ports.json`](../../backend/data/sample/zetaris/poe_ports.json),
tests `test_get_ports_encodes_filters_safely`, `test_get_ports_normalizes_rest_cells`
and `test_sample_ports_end_to_end_with_evaluator` in
[`test_zetaris_adapter.py`](../../backend/tests/test_zetaris_adapter.py).

Every runtime query first passes a lexical read-only guard. It permits one
statement beginning with `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN` or `WITH`, and
rejects DDL/DML keywords outside string literals. The live client uses a 15-second
timeout and retries connection failures and HTTP 5xx twice, with 0.5/1.0-second
backoff. `SAMPLE_MODE=true`, or a missing `ZETARIS_API_KEY`, prevents network use.
Evidence: `dry_run`, `_live_rows` and `__init__` in
[`zetaris.py`](../../backend/app/adapters/zetaris.py),
plus the guard, retry and sample tests in
[`test_zetaris_adapter.py`](../../backend/tests/test_zetaris_adapter.py).

In the run pipeline, `fetch_ports` calls the adapter for the requested zone. If a
live query fails, it writes a `ZetarisAdapter` trace event with
`status: "fallback"` and reads the same zone from the sample fixture, so the run
continues. Evidence: `fetch_ports` in
[`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py) and
`test_zetaris_live_failure_falls_back_to_sample`. Against the local Zetaris
instance, `test_live_zone_through_real_zetaris` passed, and the recorded live run
read two Bermuda ports, where the fixture has one
([`01_bermuda.live_nemotron.json`](../../output_examples/01_bermuda.live_nemotron.json)).

Setup is dry-run by default. It is deliberately separate from the application
adapter because it executes DDL:

```bash
cd backend
.venv/bin/python scripts/zetaris_setup.py

set -a
source ../.env
set +a
.venv/bin/python scripts/zetaris_setup.py --apply
```

`--apply` executes the four SQL statements, then executes these checks and stops
unless the first result is exactly 1,169:

```sql
SELECT COUNT(*) FROM blue_intel.poe_ports;
SELECT name, zone_name, lat, lon FROM blue_intel.poe_ports LIMIT 5;
```

To repeat only those checks through the read-only adapter:

```bash
SAMPLE_MODE=false .venv/bin/python -c 'from app.adapters.zetaris import ZetarisClient as Z; c=Z(); print(c.query("SELECT COUNT(*) FROM blue_intel.poe_ports")); print(c.query("SELECT name, zone_name, lat, lon FROM blue_intel.poe_ports LIMIT 5", limit=5))'
```

Evidence for all three commands and both verification statements:
[`zetaris_setup.py`](../../backend/scripts/zetaris_setup.py).

## 2. Meterless H-MEM engine: verification memory

One Meterless Engine is implemented: **H-MEM**. Markovian, World Model and Scout
Intent are not used.

`backend/app/engines/hmem/` is a Python port of the Meterless H-MEM TypeScript
reference at upstream commit `1742dec56a66e58eef9dda2d2b865823758ca8cd`,
licensed Apache-2.0. It includes the deterministic 64-dimensional FNV-1a
embedder, exact hybrid retrieval weights/defaults, tiered store, model-free
mining with an optional synchronous model hook, conflict gate, sleep guardrails,
approval-only dreaming, and the 17 canonical trust-ledger actions. Evidence:
[`README.md`](../../backend/app/engines/hmem/README.md),
[`embeddings.py`](../../backend/app/engines/hmem/embeddings.py),
[`memory_retrieval.py`](../../backend/app/engines/hmem/memory_retrieval.py),
[`types.py`](../../backend/app/engines/hmem/types.py),
and the copied [`LICENSE`](../../backend/app/engines/hmem/LICENSE).

The test fixture is byte-for-byte identical to Meterless's 13 official vectors
(SHA-256 `10afb5a07233466576ba6feb0d88408488909ba2721ee9157fdb932132917029`).
The parametrized test runs all 13 cases: record validation, feedback deltas,
ranking order, sleep guardrails, conflict gate, ledger audit and dream boundary.
Evidence: [`hmem_vectors.json`](../../backend/tests/fixtures/hmem_vectors.json)
and [`test_hmem_conformance.py`](../../backend/tests/test_hmem_conformance.py).

`recall_node` queries by normalized port name plus zone and attaches the top five
matches, including score, source and provenance, as `port["memory"]`.
`remember_node` writes one long-term memory per finalised port. A repeated verdict
gives the prior active memory `helpful` feedback. A changed verdict creates and
resolves a conflict: the previous record remains stored and receives
`supersededBy`; it is not deleted. Evidence: [`memory.py`](../../backend/app/agents/memory.py)
and tests `test_remember_then_recall_second_run`, `test_same_verdict_helpful` and
`test_verdict_flip_retains_old_and_audits` in
[`test_hmem_memory.py`](../../backend/tests/test_hmem_memory.py).

Working and long-term tiers are JSONL files under `HMEM_DIR` (default
`data/hmem/`); short-term records are memory-only. The separate `ledger.jsonl`
is append-only, validates all 17 action names, and stores previous/new snapshots
for audited mutations. Evidence: [`memory_store.py`](../../backend/app/engines/hmem/memory_store.py),
[`trust_ledger.py`](../../backend/app/engines/hmem/trust_ledger.py),
and `test_jsonl_persistence_and_ephemeral_tier` in
[`test_hmem_memory.py`](../../backend/tests/test_hmem_memory.py).

### Working feature: ResearchAgent

ResearchAgent is the retry step of the pipeline. For each port the evaluator
routes to retry, it searches that port's recalled memories for a source that
`is_official_source` accepts. If it finds one, it adds the URL to the port's
`source_urls` with provenance `hmem`, and the evaluator re-scores the port with
that evidence. Otherwise it records `no prior official source`. Every outcome is
a `ResearchAgent` trace event. Evidence: `research` and
`_remembered_official_sources` in
[`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py).

`test_research_uses_remembered_official_source` runs the same port twice. In the
first run the port has a government source and ends as a flag at 60. In the second
run its source is missing, so it scores 34 and is routed to retry. ResearchAgent
restores the remembered source, and the port ends as a flag at 60 after one retry,
with source provenance `hmem`. The test asserts the `hmem_official_source` outcome,
the restored URL and its provenance, the final verdict `flag` with confidence
above 40, and exactly one retry. The 34 and 60 values were measured on the same
scenario; the test checks the threshold rather than the exact numbers.
`test_second_run_recalls_first_run_memories` checks that a second CLI run in the
same `HMEM_DIR` recalls the first run's memories.

Prior verdicts are evidence for a retry only. They do not change the scoring
formula and never mark a port as cleared by themselves.

## 3. Meterless Nightshift: AI provider

[`generator.py`](../../backend/app/core/generator.py) connects to the Nightshift
OpenAI-compatible runtime. It reads the official variables first:
`METERLESS_BASE_URL` (default `http://127.0.0.1:8088/v1`),
`METERLESS_RUNTIME_TOKEN` and `METERLESS_MODEL` (default `meterless/auto`). The
legacy `MODEL_BASE_URL`, `MODEL_API_KEY` and `MODEL_NAME` are read only when the
official name is unset. Each call probes `GET {base}/models`, then sends
`POST {base}/chat/completions` with the bearer token and the `meterless-app` /
`meterless-scope` headers. Evidence: `generate`, `_probe` and `_complete` in
[`generator.py`](../../backend/app/core/generator.py);
`test_official_env_names_and_default_model`,
`test_legacy_env_names_only_when_official_unset` and
`test_nightshift_success_headers_actual_model_and_trace`.

Latency is bounded:

- The probe has a 3-second timeout, and its result is cached for 60 seconds.
- Each provider has a 90-second wall-clock budget, shared by the request and at
  most one retry; a request that times out is not retried.
- The whole call is capped at 150 seconds before the sample fallback.

Evidence: `REQUEST_TIMEOUT_S`, `GENERATE_BUDGET_S`, `worst_case_seconds` and
`_request` in [`generator.py`](../../backend/app/core/generator.py);
`test_worst_case_latency_budget` (93 seconds worst case before falling back from
Nightshift, 150 seconds for the whole call), `test_hanging_providers_respect_budget`
and `test_chat_retries_at_most_once_then_falls_back`.

Some models return their reasoning inside the reply, ending with `</think>`.
The generator removes it before the text is used; a reply that contains only
reasoning is invalid and falls back to the next provider. Evidence:
`_strip_reasoning` in [`generator.py`](../../backend/app/core/generator.py),
`test_reasoning_is_stripped_from_content` and
`test_reasoning_only_answer_is_invalid_and_falls_back`.

Fallback order: Nightshift, then NVIDIA direct only if `NVIDIA_API_KEY` is set,
then the caller's `sample_fn`. With `SAMPLE_MODE=true` no provider is called.
Results and traces record `provider`, `requested_model`, `served_model` (taken
from the response, never relabelled) and a sanitized `fallback_reason`. Evidence:
`test_offline_nightshift_nvidia_fallback`,
`test_no_keys_offline_skips_nvidia_straight_to_sample`,
`test_sample_fn_runs_caller_logic_in_sample_mode` and
`test_sample_fn_used_when_providers_fail`.

### Working feature: BriefingAgent

BriefingAgent sends the zone's finalised ports (name, verdict, confidence, reasons,
sources) to `generator.generate()` and asks for a short clearance brief for
sailors: which ports are confirmed, which are flagged and why, with their sources.
Its `sample_fn` builds the same brief deterministically from the same port data,
so sample mode runs the real logic on real inputs. The output's `llm` field and
the `BriefingAgent` trace event record the provider and served model. Evidence:
`write_brief`, `brief_prompt` and `sample_brief` in
[`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py);
`test_sample_brief_is_built_from_port_data` and `test_live_brief_served_by_nemotron`.

## 4. NVIDIA: Nemotron through Nightshift

NVIDIA contributes the Nemotron models that Nightshift serves to the generator.
The recorded live run on 22 October 2026 used
`METERLESS_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b`. Nightshift's routing
served `nvidia/nemotron-3.5-super-vl-120b-a12b`, a different Nemotron model.
The application did not choose that model; it records what the runtime reports.
Evidence: `llm` in
[`01_bermuda.live_nemotron.json`](../../output_examples/01_bermuda.live_nemotron.json)
(`provider: "nightshift"`) and the `MeterlessGenerator` event in
[`01_bermuda.live_nemotron.trace.jsonl`](../../output_examples/01_bermuda.live_nemotron.trace.jsonl)
(`requested_model` and `served_model`).

Two live tests passed against local Nightshift with `NIGHTSHIFT_LIVE=1`:

- `test_live_brief_served_by_nemotron` runs the pipeline and asserts
  `provider == "nightshift"`, a served model containing `nemotron`, and a brief
  that names the zone's port.
- `test_live_nightshift_nemotron` calls the generator directly and asserts the
  same provider and model, plus a correct JSON port extraction.

NVIDIA direct (`NVIDIA_API_KEY`, `NEMOTRON_MODEL`) is an optional fallback in
[`generator.py`](../../backend/app/core/generator.py). It was not configured for
the recorded run.

## 5. Agent flow and traces

```text
ZetarisAdapter.get_ports
  -> HMemAgent.recall
  -> EvaluatorAgent.evaluate
  -> [while route == retry, at most 2 times: ResearchAgent -> prepare_retry -> evaluate]
  -> EvaluatorAgent.finalise
  -> BriefingAgent -> MeterlessGenerator
  -> HMemAgent.remember
```

The orchestrator is plain Python; LangGraph is not a dependency of this
repository. Every step shares one `run_id`. Synchronous steps run in daemon
threads under a 5-minute run timeout, so a hung step returns a partial result
with an `error` field. Evidence: `_run`, `run_pipeline` and `RUN_TIMEOUT_S` in
[`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py);
`test_trace_has_every_agent_one_run_id_and_retry`,
`test_timeout_returns_partial_result`.

Each agent appends JSONL to `logs/trace-<run_id>.jsonl` and to stdout
(`TRACE_LOG_PATH` overrides the file, `TRACE_STDOUT=0` silences stdout). The lines
below are copied unchanged from the recorded live trace
[`01_bermuda.live_nemotron.trace.jsonl`](../../output_examples/01_bermuda.live_nemotron.trace.jsonl).
They are lines 1, 2, 3, 5, 7, 9, 19, 21, 22, 23 and 25. The omitted lines are the
same events for Port of Hamilton, and the second retry round with the final evaluation. The recalled memories
come from earlier local runs of the same input file, which is why they carry the
same `run_id` label.

```jsonl
{"timestamp": "2026-10-22T21:41:09.427362+00:00", "agent_name": "RunPipeline", "run_id": "example-bermuda", "action": "run_start", "input_summary": {"zone_name": "Bermuda", "timeout_s": 300.0}}
{"timestamp": "2026-10-22T21:41:11.206777+00:00", "agent_name": "ZetarisAdapter", "run_id": "example-bermuda", "action": "zetaris_query", "input_summary": {"sql": "SELECT name, lat, lon, to_json(source_urls) AS source_urls, validated, geocode_source, zone_name, mrgid, id FROM blue_intel.poe_ports WHERE zone_name = decode(unhex('4265726d756461'), 'UTF-8')"}, "row_count": 2, "duration_ms": 1778.974, "mode": "live", "status": "ok"}
{"timestamp": "2026-10-22T21:41:11.216303+00:00", "agent_name": "HMemAgent", "run_id": "example-bermuda", "action": "recall", "input_summary": {"port_name": "Port of St. George’s", "zone_name": "Bermuda"}, "memories": [{"id": "mem-1", "content": "Port Port of St. George’s (Bermuda): verdict flag; official source none; reasons unknown source; single extractor; inside the EEZ; no direct source (empty URLs or synthesis only); single geocoder, not cross-checked; unconfirmed after max retries", "score": 0.26436089189508927, "source": "evaluator", "provenance": {"origin": "model_response", "learnedAt": 1792702150144, "label": "evaluator run example-bermuda", "refs": ["example-bermuda"]}, "supersededBy": null}, {"id": "mem-3", "content": "Port Port of St. George’s (Bermuda): verdict flag; official source none; reasons unknown source; single extractor; inside the EEZ; no direct source (empty URLs or synthesis only); single geocoder, not cross-checked; unconfirmed after max retries", "score": 0.26436089189508927, "source": "evaluator", "provenance": {"origin": "model_response", "learnedAt": 1792704685402, "label": "evaluator run example-bermuda", "refs": ["example-bermuda"]}, "supersededBy": null}, {"id": "mem-5", "content": "Port Port of St. George’s (Bermuda): verdict flag; official source none; reasons unknown source; single extractor; inside the EEZ; no direct source (empty URLs or synthesis only); single geocoder, not cross-checked; unconfirmed after max retries", "score": 0.24673763284556377, "source": "evaluator", "provenance": {"origin": "model_response", "learnedAt": 1792704768070, "label": "evaluator run example-bermuda", "refs": ["example-bermuda"]}, "supersededBy": null}], "handoff": {"from": "HMemAgent", "to": "EvaluatorAgent"}}
{"timestamp": "2026-10-22T21:41:11.219311+00:00", "agent_name": "EvaluatorAgent", "run_id": "example-bermuda", "action": "evaluate_port", "port_name": "Port of St. George’s", "input_summary": {"port_name": "Port of St. George’s", "retry_count": 0}, "verdict": "retry", "reasons": ["unknown source", "single extractor", "inside the EEZ", "no direct source (empty URLs or synthesis only)", "single geocoder, not cross-checked"], "retry_hint": "find an official source"}
{"timestamp": "2026-10-22T21:41:11.219717+00:00", "agent_name": "ResearchAgent", "run_id": "example-bermuda", "action": "research_port", "input_summary": {"port_name": "Port of St. George’s", "zone_name": "Bermuda", "retry_hint": "find an official source", "memories": 3}, "outcome": "no prior official source", "handoff": {"from": "ResearchAgent", "to": "EvaluatorAgent"}}
{"timestamp": "2026-10-22T21:41:11.219942+00:00", "agent_name": "EvaluatorAgent", "run_id": "example-bermuda", "action": "prepare_retry", "port_name": "Port of St. George’s", "input_summary": {"port_name": "Port of St. George’s", "retry_count": 1}, "verdict": "retry", "reasons": ["unknown source", "single extractor", "inside the EEZ", "no direct source (empty URLs or synthesis only)", "single geocoder, not cross-checked"], "retry_hint": "find an official source", "handoff": {"from": "EvaluatorAgent", "to": "retry"}}
{"timestamp": "2026-10-22T21:41:11.220747+00:00", "agent_name": "EvaluatorAgent", "run_id": "example-bermuda", "action": "finalise_port", "port_name": "Port of St. George’s", "input_summary": {"port_name": "Port of St. George’s", "retry_count": 2}, "verdict": "flag", "reasons": ["unknown source", "single extractor", "inside the EEZ", "no direct source (empty URLs or synthesis only)", "single geocoder, not cross-checked", "unconfirmed after max retries"]}
{"timestamp": "2026-10-22T21:41:38.903449+00:00", "agent_name": "MeterlessGenerator", "action": "generate", "run_id": "example-bermuda", "provider": "nightshift", "requested_model": "nvidia/nemotron-3.5-lightning-30b-a3b", "served_model": "nvidia/nemotron-3.5-super-vl-120b-a12b", "duration_ms": 27682.128, "status": "success", "input_summary": {"prompt": "Zone: Bermuda\nFinalised ports (JSON):\n[{\"name\": \"Port of St. George’s\", \"verdict\": \"flag\", \"confidence\": 34, \"why\": [\"no direct source (empty URLs or synthesis only)\", \"single geocoder, not cross-chec", "role": "brief"}, "fallback_reason": null}
{"timestamp": "2026-10-22T21:41:38.905033+00:00", "agent_name": "BriefingAgent", "run_id": "example-bermuda", "action": "brief", "input_summary": {"zone_name": "Bermuda", "ports": 2}, "provider": "nightshift", "served_model": "nvidia/nemotron-3.5-super-vl-120b-a12b", "fallback_reason": null, "handoff": {"from": "BriefingAgent", "to": "HMemAgent"}}
{"timestamp": "2026-10-22T21:41:38.911054+00:00", "agent_name": "HMemAgent", "run_id": "example-bermuda", "action": "remember", "input_summary": {"port_name": "Port of St. George’s", "zone_name": "Bermuda"}, "memory_id": "mem-7", "outcome": "helpful", "handoff": {"from": "EvaluatorAgent", "to": "HMemAgent"}}
{"timestamp": "2026-10-22T21:41:38.913588+00:00", "agent_name": "RunPipeline", "run_id": "example-bermuda", "action": "run_end", "status": "ok", "error": null, "summary": {"flag": 2}, "timings_ms": {"ZetarisAdapter.get_ports": 1784.7, "HMemAgent.recall": 4.7, "EvaluatorAgent.evaluate": 2.8, "ResearchAgent.research": 0.5, "EvaluatorAgent.prepare_retry": 0.2, "EvaluatorAgent.finalise": 0.1, "BriefingAgent.brief": 27684.5, "HMemAgent.remember": 7.6, "total": 29485.1}}
```

## 6. How judges run it

[`docs/RUNNING.md`](../RUNNING.md) gives the fresh-clone commands: a six-package
install, sample mode with no credentials (`python backend/run.py --input
input_examples/01_bermuda.json`), live mode with `.env`, the HTTP server
(`--serve`, `POST /run`, `GET /healthz`) and where traces are written.
`test_fresh_clone_cli_succeeds_in_sample_mode` runs that CLI in a subprocess with
no `MONGO_URL`, no keys and no `.env`, and `test_post_run_returns_same_schema`
checks the HTTP endpoint. Inputs are in [`input_examples/`](../../input_examples/);
generated outputs and traces are in [`output_examples/`](../../output_examples/).

To run the sponsor tests:

```bash
cd backend
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_test POE_AUTO_REFRESH=0 \
  .venv/bin/python -m pytest tests/test_run_pipeline.py tests/test_zetaris_adapter.py \
  tests/test_hmem_conformance.py tests/test_hmem_memory.py tests/test_generator.py \
  tests/test_evaluator.py -v
```

The live tests need the local services and `.env` credentials:

```bash
set -a
source ../.env
set +a
ZETARIS_LIVE=1 NIGHTSHIFT_LIVE=1 \
  MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_test POE_AUTO_REFRESH=0 \
  .venv/bin/python -m pytest tests/test_run_pipeline.py tests/test_zetaris_adapter.py \
  tests/test_generator.py -v -k live
```

## 7. Limitations

- **Sample ports end as flags.** The Zetaris view and the sample fixture carry
  name, location, validation, geocoder and source URLs, but none of the reading,
  geocoder-agreement or external-check fields that `score_port` rewards. A port
  with a government source therefore reaches at most 60 (source 30, single
  extractor 12, inside the EEZ 18), and the evaluator needs more than 60 for
  `pass`. Evidence: the view in [`zetaris_setup_poe.sql`](../../backend/scripts/zetaris_setup_poe.sql),
  [`poe_ports.json`](../../backend/data/sample/zetaris/poe_ports.json),
  `score_port` in [`poe_confidence.py`](../../backend/app/services/poe_confidence.py)
  and `_verdict` in [`evaluator.py`](../../backend/app/agents/evaluator.py).
- **Nightshift may serve a different Nemotron than requested.** The served model
  is recorded, not chosen by the application (section 4).
- **Merge order.** The work spans PRs #26 (Zetaris), #28 (H-MEM), #29 (evaluator
  follow-ups), #30 (Nightshift generator) and #32 (run pipeline), which must be
  merged in that order before this document (#31). `docs/RUNNING.md` tells judges
  to clone the default branch.
- The 1,169-port GeoJSON is a repository snapshot, not current clearance advice;
  live Zetaris reads the REST table backed by that snapshot. The sample fixture
  contains only 20 rows, one per zone.
- The Zetaris setup is not idempotent and has no DDL rollback. It is an
  administrator command, never an agent action. Evidence: module docstring and
  `--apply` path in [`zetaris_setup.py`](../../backend/scripts/zetaris_setup.py).
- The SQL guard is conservative lexical validation, not a SQL parser or database
  permission boundary. The live Zetaris account should also be read-only.
  Evidence: `ZetarisClient.dry_run` docstring in
  [`zetaris.py`](../../backend/app/adapters/zetaris.py).
- H-MEM's default mining path is heuristic and model-free. The optional model
  hook is synchronous and is not used by `recall_node` or `remember_node`.
  Evidence: [`memory_mining.py`](../../backend/app/engines/hmem/memory_mining.py)
  and [`memory.py`](../../backend/app/agents/memory.py).
- H-MEM tier files and the ledger are not a multi-file transaction. Dream
  proposals, conflict queues and sleep backups are instance-local. Evidence:
  [`README.md`](../../backend/app/engines/hmem/README.md).
- The memory node's process lock uses `filelock`, which is installed by
  [`RUNNING.md`](../RUNNING.md) and pinned in
  [`requirements.txt`](../../backend/requirements.txt), and works on Windows,
  Linux and macOS. Without `filelock` it falls back to `fcntl` (Linux and macOS),
  then to a thread-only lock that does not protect against other processes.
  Evidence: `_acquire_lock` and `_engine` in
  [`memory.py`](../../backend/app/agents/memory.py), and
  `test_thread_only_lock_without_filelock_or_fcntl`,
  `test_fcntl_lock_released_exactly_once` and
  `test_filelock_path_holds_and_releases` in
  [`test_hmem_memory.py`](../../backend/tests/test_hmem_memory.py).
- `is_official_source` is a hostname naming heuristic, not proof of government
  ownership and not an exhaustive allowlist. Evidence: `is_official_source` in
  [`evaluator.py`](../../backend/app/agents/evaluator.py) and its cases in
  [`test_evaluator.py`](../../backend/tests/test_evaluator.py).
- In sample mode no model is called; the brief comes from `sample_brief`.

## 8. Pre-existing and new code

The confidence formula and production write path are pre-existing:
`score_port()` and `apply_score()` in
[`poe_confidence.py`](../../backend/app/services/poe_confidence.py).
The existing `backend/app/services/poe_*.py` pipeline is also pre-existing. The
evaluator imports those functions rather than copying or changing them; evidence:
[`evaluator.py`](../../backend/app/agents/evaluator.py).

The sponsor integration, evaluator and pipeline files described above are new
hackathon work, all committed on 22 October 2026 or later:

| Area | PR | New-work commits |
| --- | ---: | --- |
| Evaluator node and trace/retry behavior | [#25](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/25) | `d8ae5fa`, `313733e`, `80362ca`, `139c751` |
| Zetaris adapter, setup, fixtures and integration tests | [#26](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/26) | `45f61f7`, `2ac638f`, `1d3f908`, `72e32c4` |
| Meterless H-MEM port and memory nodes | [#28](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/28) | `eff8c67` |
| Strict official-source follow-up | [#29](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/29) | `bee620b` |
| Nightshift generator and opt-in LLM hook | [#30](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/30) | `6688bdc`, `860f24d`, `eb5701a`, `2df1406` |
| This write-up | [#31](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/31) | `85e840a` and this update |
| Run pipeline, CLI, `POST /run`, examples and docs | [#32](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/32) | `f11d972`, `04f9368`, `6f1265c`, `44a7aeb`, `4cdd51f`, `953b11d`, `1892f87` |
