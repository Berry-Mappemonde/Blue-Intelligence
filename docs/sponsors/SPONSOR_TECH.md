# Sponsor technology: Zetaris, Meterless and NVIDIA

This note explains how each sponsor technology is used in the PoE Reconciler and
where the evidence is. Each claim points to a file or a test in this repository.
All paths are relative to this file and exist on this branch, which is based on the
V2 integration branch `feat/integrate-poe-pipeline` (PR #33). That branch already
contains the runnable pipeline from PR #32 and the registry tiers from PR #34
(merge order: see [Limitations](#7-limitations)).

| Sponsor | Role in the product | Code | Working feature | Test evidence |
| --- | --- | --- | --- | --- |
| Zetaris | Data layer: every run reads its ports through Zetaris SQL, then checks them against UN/LOCODE and the World Port Index held in Zetaris | [`zetaris.py`](../../backend/app/adapters/zetaris.py), [`registry_check.py`](../../backend/app/agents/registry_check.py) | ZetarisAdapter: `get_ports`, then `registry_check` (evidence tier per port) | [`test_zetaris_adapter.py`](../../backend/tests/test_zetaris_adapter.py), [`test_zetaris_registries.py`](../../backend/tests/test_zetaris_registries.py), `test_live_zone_through_real_zetaris`, `test_live_registry_views_for_bermuda` |
| Meterless H-MEM engine | Verification memory across runs | [`engines/hmem/`](../../backend/app/engines/hmem/), [`memory.py`](../../backend/app/agents/memory.py) | ResearchAgent reuses a previously verified official source during retries | [`test_hmem_conformance.py`](../../backend/tests/test_hmem_conformance.py), `test_research_uses_remembered_official_source` |
| Meterless Nightshift | Primary AI provider | [`generator.py`](../../backend/app/core/generator.py) | BriefingAgent writes the sailor-facing brief | [`test_generator.py`](../../backend/tests/test_generator.py), `test_live_brief_served_by_nemotron` |
| NVIDIA | Nemotron models served through Nightshift | [`generator.py`](../../backend/app/core/generator.py), [`poe_judge.py`](../../backend/app/agents/poe_judge.py) | BriefingAgent's brief and NemotronJudge's advisory critique, both in the recorded live run | [`test_poe_judge.py`](../../backend/tests/test_poe_judge.py), `test_live_nightshift_nemotron`, [`01_bermuda.live_nemotron.json`](../../output_examples/01_bermuda.live_nemotron.json) |

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

### Independent registries and evidence tiers

`blue_intel.poe_ports` holds Blue Intelligence's own seed, so it cannot confirm
itself. Zetaris therefore also holds two third-party registries, and every run
checks each candidate against them in a `ZetarisAdapter.registry_check` step,
before H-MEM and the evaluator see it:

| Zetaris view | Source | Licence | Rows (local Zetaris) |
| --- | --- | --- | --- |
| `blue_intel.unlocode_ports` | [UN/LOCODE](https://unece.org/trade/cefact/unlocode-code-list-country-and-territory), UNECE: entries whose Function has "1" in position 1 (port) | Published by UNECE for free use; no formal licence is stated | 17,642 |
| `blue_intel.wpi_ports` | [World Port Index](https://msi.nga.mil/Publications/WPI), NGA Pub 150, including the first-port-of-entry field | US Government work, public domain | 3,807 |

The administrator setup downloads both files to a gitignored folder, registers
them as Lightning file-store tables in database `BLUE_INTEL_REGISTRIES`, exposes
them as schemastore views, and compares each view's `COUNT(*)` with the local
file. Only small real fixtures are committed. Evidence:
[`zetaris_setup_registries.sql`](../../backend/scripts/zetaris_setup_registries.sql),
[`zetaris_setup.py`](../../backend/scripts/zetaris_setup.py) (`--part registries`),
parsers in [`registry_sources.py`](../../backend/app/adapters/registry_sources.py)
(UN/LOCODE `DDMMN DDDMMW` coordinates converted to decimal degrees), and fixtures
[`unlocode_ports.json`](../../backend/data/sample/zetaris/unlocode_ports.json) and
[`wpi_ports.json`](../../backend/data/sample/zetaris/wpi_ports.json).

At runtime, `ZetarisClient.get_registry_ports(country_iso2, bbox, source)` reads one
view through the same read-only `query()`. Filters are validated before they
enter SQL: the country can only be two ASCII letters, and the bounding box must
be finite and ordered. Each port then gets two kinds of evidence:

- **Registry match:** an entry in the same country with the same name, and, when
  both sides have coordinates, within 25 km. Names are compared without case,
  accents or punctuation; "Port of" and similar words are removed; St becomes
  Saint; WPI alternate names and UN/LOCODE names without diacritics count. A name
  and country match beyond 25 km is recorded as `coord_mismatch` with its
  distance. It is not a match, and the port is kept.
- **Official source evidence:** a URL that passes `is_official_source()` *and* whose
  text names the port within ~200 characters of an entry term (strong or weak, see
  below). A mention inside an address or contact listing, or with no entry term
  nearby, does not count. The text is fetched now or is a stored snippet of an
  earlier fetch (PR #41); it is never model output.

| Tier | Label | Evidence |
| --- | --- | --- |
| `tier1` | Official Commercial Port of Entry | official source evidence and a registry match |
| `tier2` | Official Yachting Port of Entry | official source evidence, no registry match (usual for marinas) |
| `tier_registered` | Registered port, entry status unverified | registry match only |
| `tier3` | Unconfirmed - review needed | neither |

A registry listing alone never establishes port-of-entry status: its reason says
so in the trace and in the brief. The WPI first-port-of-entry field is recorded
as supporting evidence only. Each port carries `registry` (`tier`, `label`,
`validation`, `matches`, `official_evidence`, `coord_mismatch`,
`first_port_of_entry`, `reasons`), and each check is a `ZetarisAdapter`
`registry_check` trace event whose status is the tier. If the live registry
query fails, the check reads the fixtures; an outage with no fallback leaves
ports unconfirmed, never official. Evidence:
[`registry_check.py`](../../backend/app/agents/registry_check.py),
`check_registries` in [`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py),
and in [`test_zetaris_registries.py`](../../backend/tests/test_zetaris_registries.py):
`test_25_km_gate_accepts_22_km_and_flags_beyond_as_coord_mismatch`,
`test_coord_mismatch_is_recorded_not_dropped`,
`test_tier1_official_source_and_registry`,
`test_tier2_official_source_without_registry_match`,
`test_tier_registered_never_claims_port_of_entry`,
`test_tier3_neither_and_traced`,
`test_grounding_needs_fetched_text_for_the_port_s_own_urls`,
`test_live_failure_falls_back_to_fixtures` and
`test_outage_without_fallback_never_marks_official`.
`test_live_registry_views_for_bermuda` passed against local Zetaris.

**What the tiers can show today (PR #41).** Generation builds evidence records
from the official pages it fetched, deterministically: the port, the URL and its
domain, a verbatim snippet of at most 400 characters around the grounded mention,
the SHA-256 of the full fetched text, the fetch time and extraction level. At most
three per port are stored in the Mongo collection `poe_evidence`, keyed on zone,
port and URL ([`evidence_store.py`](../../backend/app/adapters/evidence_store.py)).
`run.py`, `POST /run` and `POST /api/poe/verify` read ports from Zetaris, so their
registry step (`check_registries` in
[`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py)) looks the records up
by zone and runs the same
check on each snippet before it counts (`evidence_source: "stored_snippet"`,
against `"fetched_now"` during generation). In sample mode, or when Mongo is
unreachable, the lookup reads small verbatim snapshots of real official pages
([`backend/data/sample/official_pages/`](../../backend/data/sample/official_pages/),
with a [`README`](../../backend/data/sample/official_pages/README.md) saying why each
page qualifies) and builds the records the same way. A failed lookup gives no
evidence and never an official tier; each lookup is a `ZetarisAdapter`
`evidence_lookup` trace event. Evidence:
[`test_evidence_store.py`](../../backend/tests/test_evidence_store.py).

A *strong* entry term is enough on its own: port(s) of entry, entry port,
clearing/clear customs, clear in, clearance port, designated port, designated
marina, port of call for clearing (with French, Spanish, Portuguese, Italian and
Greek equivalents). A *weak* term (customs, immigration, quarantine, harbour master)
counts only with a port, harbour, marina or quay word in the same window and a match
on the full name, not the town left after stripping "Port of": Bermuda's customs
"Long Room" in Hamilton, where goods are declared, does not make the Port of
Hamilton an entry point (`ENTRY_TERMS` and `entry_mention` in
[`registry_check.py`](../../backend/app/agents/registry_check.py)). PR #42 adds
"point(s) of entry" as a weak term, so an airport-only "point of entry" will not
count. In the sample run, 2 of the 20 sample ports are `tier1` (Port of St.
George's, Bermuda: gov.bm Customs and a Bermuda planning report; Anchorage Small
Boat Harbor, Alaska: CBP's designated marina), 2 are `tier2` (Deep water Harbor,
Antigua and Barbuda: customs.gov.ag; Conch Inn Marina, Bahamas: Bahamas Customs),
11 are `tier_registered` and 5 are `tier3`; before stored evidence it was 13 and 7.
With records in Mongo and live Zetaris, St. George's and Hamilton (Bermuda) are
`tier1`; no official page designates Angola's or the Azores' ports, so they stay at
their registry tier. With PR #45 the evaluator also uses this evidence: a `tier1` or
`tier2` port is scored with an official source, and its position can be corroborated
by a registry entry within 2.0 km. St. George's and Anchorage Small Boat Harbor then
pass at 67 (live Hamilton too), while every other sample port stays `flag`
(see [Limitations](#7-limitations)).

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
`remember_node` compares each finalised port with the latest active memory for
the same port. If the verdict and the official source are unchanged, it does not
add a record: it gives that memory H-MEM `helpful` feedback (confidence and
`accessCount` go up) and records the trace outcome `reinforced`. A changed
official source adds a new record. A changed verdict adds a record and creates and
resolves a conflict: the previous record remains stored and receives
`supersededBy`; it is not deleted. Evidence: `remember_node` in
[`memory.py`](../../backend/app/agents/memory.py) and tests
`test_remember_then_recall_second_run`,
`test_same_verdict_and_source_reinforces_without_duplicate`,
`test_changed_official_source_adds_record_without_superseding` and
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
With PR #45 a port's sources also list the official pages that designate it
(`domain: url (official evidence)`), and a port with none says "No source".
Its `sample_fn` builds the same brief deterministically from the same port data,
so sample mode runs the real logic on real inputs. The output's `llm` field and
the `BriefingAgent` trace event record the provider and served model. Evidence:
`write_brief`, `brief_prompt` and `sample_brief` in
[`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py);
`test_sample_brief_is_built_from_port_data` and `test_live_brief_served_by_nemotron`.

## 4. NVIDIA: Nemotron through Nightshift

NVIDIA contributes the Nemotron models that Nightshift serves to the generator.
Two agents call Nemotron in a live run: NemotronJudge (below) and BriefingAgent
(section 3). The recorded live run on 25 October 2026 requested
`METERLESS_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b` for both calls. Nightshift's
routing served `nvidia/nemotron-3.5-super-vl-120b-a12b` for the judge and
`nvidia/nemotron-3-ultra-550b-a55b` for the brief. The application did not choose
those models; it records what the runtime reports. Evidence: `llm` and `judge` in
[`01_bermuda.live_nemotron.json`](../../output_examples/01_bermuda.live_nemotron.json) (`provider: "nightshift"`) and the
two `MeterlessGenerator` events in
[`01_bermuda.live_nemotron.trace.jsonl`](../../output_examples/01_bermuda.live_nemotron.trace.jsonl) (`requested_model`
and `served_model`, roles `judge` and `brief`).

### Working feature: NemotronJudge, an advisory critic

After the first evaluation, NemotronJudge makes one Nemotron call per zone through
the same generator (Nightshift first). It reads only the official evidence text
the run already holds (the snippets in `registry.official_evidence`) and does not
see the pipeline's verdicts. For each port it answers `poe`, `not_poe` or
`unclear`, with a reason and a quoted excerpt. The run records
`port.judge = {verdict, reason, quoted_excerpt, excerpt_verified, disagrees}` and
one `NemotronJudge` `critique` trace event under the run's `run_id`.

- **Never overrides evidence.** It never writes a tier, validation, official
  evidence or confidence. `excerpt_verified` is true only when the quote is inside
  the evidence text, and even a verified quote is never evidence.
- **Triggers one research round.** When it calls a port the evaluator flagged a
  port of entry, that port goes through one more ResearchAgent → EvaluatorAgent
  round. The verdict still comes from `score_port`.
- **Skipped without credentials.** In `SAMPLE_MODE`, without official evidence
  text, without a provider answer, after 90 s, or with an unusable answer, the
  judge is skipped. The `critique` event then says why (`status: "skipped"`).

In the recorded live run the judge answered `poe` for both Bermuda ports, with
`excerpt_verified: true` and no disagreement with the pipeline. For Port of
Hamilton it quoted "Customs officers are stationed at Bermuda’s main ports of
entry: St. George’s L. F. Wade International Airport Hamilton" from the gov.bm
Customs page. Evidence: [`poe_judge.py`](../../backend/app/agents/poe_judge.py),
the `critique` event in [`01_bermuda.live_nemotron.trace.jsonl`](../../output_examples/01_bermuda.live_nemotron.trace.jsonl),
and [`test_poe_judge.py`](../../backend/tests/test_poe_judge.py):

- `test_judge_never_changes_tier_validation_evidence_or_confidence`
- `test_unverified_or_verified_excerpt_never_counts_as_evidence`
- `test_disagreement_on_a_flagged_port_triggers_one_evaluator_retry`
- `test_skipped_in_sample_mode_without_a_provider_call`
- `test_skipped_when_no_provider_answers_and_sample_mode_never_set`

Two live tests passed against local Nightshift with `NIGHTSHIFT_LIVE=1`:

- `test_live_brief_served_by_nemotron` runs the pipeline and asserts
  `provider == "nightshift"`, a served model containing `nemotron`, and a brief
  that names the zone's port.
- `test_live_nightshift_nemotron` calls the generator directly and asserts the
  same provider and model, plus a correct JSON port extraction.

NVIDIA direct (`NVIDIA_API_KEY`, `NEMOTRON_MODEL`) is an optional fallback in
[`generator.py`](../../backend/app/core/generator.py). It was not configured for
the recorded run.

The recorded run read its ports and registries from live Zetaris. No Mongo
evidence store was available, so the evidence lookup used its documented fallback:
the committed snapshots of the gov.bm Customs page and the Bermuda planning report
(`evidence_lookup` event: `status: "fallback"`, `source: "sample_pages"`; see
[Limitations](#7-limitations)).

## 5. Agent flow and traces

```text
ZetarisAdapter.get_ports
  -> ZetarisAdapter.registry_check
  -> HMemAgent.recall
  -> EvaluatorAgent.evaluate
  -> NemotronJudge.critique -> MeterlessGenerator
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
They are lines 1, 2, 3, 8, 10, 11, 12, 13, 14, 15, 16 and 18. The omitted lines are the two registry
queries, the `registry_check` events (tier1 for both ports, with the evidence
snippets and registry matches), and the same recall and remember events for Port of
Hamilton. H-MEM started empty for this run, so nothing is recalled and both ports
are `created`. Line 13 (the `critique` event) was patched after the recording: each
judgment's `reason` and `quoted_excerpt` were copied verbatim from `port.judge` in
the output JSON, because the event now carries them.

Both ports pass on the first evaluation, so this run has no retry. A retry round
is in `output_examples/04_benin.trace.jsonl`: EvaluatorAgent critiques Benin's
port, two ResearchAgent rounds follow, and the port is finalised as a flag. The
judge-triggered round is covered by
`test_disagreement_on_a_flagged_port_triggers_one_evaluator_retry`.

```jsonl
{"timestamp": "2026-10-25T18:26:39.853172+00:00", "agent_name": "RunPipeline", "run_id": "example-bermuda", "action": "run_start", "input_summary": {"zone_name": "Bermuda", "timeout_s": 300.0}}
{"timestamp": "2026-10-25T18:26:45.244813+00:00", "agent_name": "ZetarisAdapter", "run_id": "example-bermuda", "action": "zetaris_query", "input_summary": {"sql": "SELECT name, lat, lon, to_json(source_urls) AS source_urls, validated, geocode_source, zone_name, mrgid, id FROM blue_intel.poe_ports WHERE zone_name = decode(unhex('4265726d756461'), 'UTF-8')"}, "row_count": 2, "duration_ms": 5391.09, "mode": "live", "status": "ok"}
{"timestamp": "2026-10-25T18:26:47.503712+00:00", "agent_name": "ZetarisAdapter", "run_id": "example-bermuda", "action": "evidence_lookup", "mode": "live", "status": "fallback", "source": "sample_pages", "records": 3, "records_by_port": {"saint george": 2, "hamilton": 1}, "input_summary": {"mrgid": 8402, "ports": 2}, "error": "ServerSelectionTimeoutError: 127.0.0.1:1: [Errno 61] Connection refused (configured timeouts: socketTimeoutMS: 2000.0ms, connectTimeoutMS: 2000.0ms),"}
{"timestamp": "2026-10-25T18:26:49.775618+00:00", "agent_name": "HMemAgent", "run_id": "example-bermuda", "action": "recall", "input_summary": {"port_name": "Port of St. George’s", "zone_name": "Bermuda"}, "memories": [], "handoff": {"from": "HMemAgent", "to": "EvaluatorAgent"}}
{"timestamp": "2026-10-25T18:26:49.777937+00:00", "agent_name": "EvaluatorAgent", "run_id": "example-bermuda", "action": "evaluate_port", "port_name": "Port of St. George’s", "input_summary": {"port_name": "Port of St. George’s", "retry_count": 0}, "verdict": "pass", "reasons": ["government source", "single extractor", "inside the EEZ, geocoders agree", "coordinates corroborated by WPI BMSGE, 0.67 km"], "geocode_corroboration": {"source": "wpi", "code": "BMSGE", "distance_km": 0.67}}
{"timestamp": "2026-10-25T18:26:49.777986+00:00", "agent_name": "EvaluatorAgent", "run_id": "example-bermuda", "action": "evaluate_port", "port_name": "Port of Hamilton", "input_summary": {"port_name": "Port of Hamilton", "retry_count": 0}, "verdict": "pass", "reasons": ["government source", "single extractor", "inside the EEZ, geocoders agree", "coordinates corroborated by WPI BMBDA, 0.93 km"], "geocode_corroboration": {"source": "wpi", "code": "BMBDA", "distance_km": 0.93}}
{"timestamp": "2026-10-25T18:27:11.708597+00:00", "agent_name": "MeterlessGenerator", "action": "generate", "run_id": "example-bermuda", "provider": "nightshift", "requested_model": "nvidia/nemotron-3.5-lightning-30b-a3b", "served_model": "nvidia/nemotron-3.5-super-vl-120b-a12b", "duration_ms": 21930.164, "status": "success", "input_summary": {"prompt": "Zone: Bermuda\nCandidate ports:\n- Port of St. George’s\n- Port of Hamilton\nOfficial texts:\n[1] https://www.gov.bm/department/customs\n. Customs officers work in partnership with the Bermuda Police Servic", "role": "judge"}, "fallback_reason": null}
{"timestamp": "2026-10-25T18:27:11.710493+00:00", "agent_name": "NemotronJudge", "run_id": "example-bermuda", "action": "critique", "input_summary": {"zone_name": "Bermuda", "ports": 2, "evidence_texts": 3}, "status": "ok", "reason": null, "provider": "nightshift", "served_model": "nvidia/nemotron-3.5-super-vl-120b-a12b", "retry_requested": [], "judgments": [{"port_name": "Port of St. George’s", "verdict": "poe", "port_verdict": "pass", "excerpt_verified": true, "disagrees": false, "reason": "Listed as a main port of entry; St. George’s harbour is the requisite Port of Call for clearing Customs.", "quoted_excerpt": "St. George’s harbour is the requisite Port of Call for clearing Customs for all non-commercial vessels entering Bermuda."}, {"port_name": "Port of Hamilton", "verdict": "poe", "port_verdict": "pass", "excerpt_verified": true, "disagrees": false, "reason": "Listed among Bermuda’s main ports of entry where customs officers are stationed.", "quoted_excerpt": "Customs officers are stationed at Bermuda’s main ports of entry: St. George’s L. F. Wade International Airport Hamilton"}], "handoff": {"from": "NemotronJudge", "to": "EvaluatorAgent"}}
{"timestamp": "2026-10-25T18:27:41.489131+00:00", "agent_name": "MeterlessGenerator", "action": "generate", "run_id": "example-bermuda", "provider": "nightshift", "requested_model": "nvidia/nemotron-3.5-lightning-30b-a3b", "served_model": "nvidia/nemotron-3-ultra-550b-a55b", "duration_ms": 29777.359, "status": "success", "input_summary": {"prompt": "Zone: Bermuda\nFinalised ports (JSON):\n[{\"name\": \"Port of St. George’s\", \"verdict\": \"pass\", \"confidence\": 67, \"why\": [\"coordinates corroborated by WPI BMSGE, 0.67 km\"], \"tier\": \"Official Commercial Por", "role": "brief"}, "fallback_reason": null}
{"timestamp": "2026-10-25T18:27:41.490154+00:00", "agent_name": "BriefingAgent", "run_id": "example-bermuda", "action": "brief", "input_summary": {"zone_name": "Bermuda", "ports": 2}, "provider": "nightshift", "served_model": "nvidia/nemotron-3-ultra-550b-a55b", "fallback_reason": null, "handoff": {"from": "BriefingAgent", "to": "HMemAgent"}}
{"timestamp": "2026-10-25T18:27:41.497639+00:00", "agent_name": "HMemAgent", "run_id": "example-bermuda", "action": "remember", "input_summary": {"port_name": "Port of St. George’s", "zone_name": "Bermuda"}, "memory_id": "mem-1", "outcome": "created", "handoff": {"from": "EvaluatorAgent", "to": "HMemAgent"}}
{"timestamp": "2026-10-25T18:27:41.502599+00:00", "agent_name": "RunPipeline", "run_id": "example-bermuda", "action": "run_end", "status": "ok", "error": null, "summary": {"pass": 2}, "timings_ms": {"ZetarisAdapter.get_ports": 5392.5, "ZetarisAdapter.registry_check": 4528.0, "HMemAgent.recall": 2.0, "EvaluatorAgent.evaluate": 2.1, "NemotronJudge.critique": 21932.6, "EvaluatorAgent.finalise": 0.4, "BriefingAgent.brief": 29779.2, "HMemAgent.remember": 11.4, "total": 61648.4}}
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

**Demo page.** `python backend/run.py --serve` also serves a page at `GET /`
(<http://localhost:8000>). It is one file,
[`demo_page.html`](../../backend/app/pipeline/demo_page.html); its only remote assets
are a pinned Leaflet build (with integrity hashes) and OpenStreetMap tiles, and it
draws an offline chart when they are unavailable. A zone is picked from
`GET /zones`, which lists live Zetaris zones, or the sample zones in sample mode or
when Zetaris is unavailable. **Run verification** streams the run from
`GET /run/stream` (server-sent events; `POST /run` is the same run as one JSON
response). The page shows:

- the mode, whether Zetaris was live, and the LLM provider and served model, with a
  "Nemotron via Nightshift" badge when the served model is a Nemotron model;
- one card per port: verdict, confidence, reasons, sources (marked when they came
  from H-MEM), memories recalled and the ResearchAgent outcome;
- the brief;
- an agent timeline built from `GET /runs/{run_id}/trace`: agents, actions,
  handoffs, retry rounds and durations.

The trace route accepts only run IDs of letters, digits, `_` and `-`. Evidence:
[`api.py`](../../backend/app/pipeline/api.py), `list_zones` and `load_trace` in
[`run_pipeline.py`](../../backend/app/pipeline/run_pipeline.py), and
`test_demo_page_serves_with_pinned_map_library_and_offline_fallback`, `test_zones_in_sample_mode`,
`test_zones_fall_back_when_zetaris_is_down`, `test_trace_route_returns_the_runs_events`
and `test_trace_route_rejects_bad_run_ids` in
[`test_run_pipeline.py`](../../backend/tests/test_run_pipeline.py).

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

- **Most sample ports end as flags.** The Zetaris view and the sample fixture
  carry name, location, validation, geocoder and source URLs, but none of the
  reading or external-check fields that `score_port` rewards, and each seed port
  has one geocode. A port with a government source therefore reaches 60 (source
  30, single extractor 12, inside the EEZ 18), and the evaluator needs more than 60
  for `pass`. With PR #45, a port with official evidence (`tier1`/`tier2`) whose
  position lies within 2.0 km of a registry entry counts that entry as an
  independent second geocode (WPI preferred, since UN/LOCODE positions are rounded
  to the minute), which raises the map part from 18 to 25. Port of St. George's
  (WPI BMSGE, 0.67 km) and Anchorage Small Boat Harbor (WPI USANC, 0.28 km) then
  pass at 67. Ports without official evidence never get this: Road Bay (Anguilla)
  and BRIDGETOWN PORT (Barbados) score 60 from government seed URLs that do not
  designate them, have registry entries within 2 km, and stay `flag`
  (`_registry_geocode_corroboration` in `evaluator.py` and its tests, PR #45). Evidence: the view in [`zetaris_setup_poe.sql`](../../backend/scripts/zetaris_setup_poe.sql),
  [`poe_ports.json`](../../backend/data/sample/zetaris/poe_ports.json),
  `score_port` in [`poe_confidence.py`](../../backend/app/services/poe_confidence.py)
  and `_verdict` in [`evaluator.py`](../../backend/app/agents/evaluator.py).
- **Nightshift may serve a different Nemotron than requested.** The served model
  is recorded, not chosen by the application (section 4). In the recorded run the
  judge and the brief were served different models.
- **NemotronJudge is advisory only.** It judges only the official text the run
  already holds, so zones without stored evidence get no judgment. Its verdicts
  never change a tier or a score (section 4).
- **The recorded live run used the evidence snapshots.** No Mongo evidence store
  was available, so `evidence_lookup` fell back to the committed official-page
  snapshots, as it does whenever Mongo is unreachable. Zetaris, the registries and
  Nightshift were live.
- **Merge order.** This document (#31) targets `feat/integrate-poe-pipeline`
  (#33), which already contains the work of #26 (Zetaris), #28 (H-MEM), #30
  (Nightshift generator), #32 (run pipeline), #34 (registry tiers), #35, #36 (V2
  UI) and #41 (stored evidence). #42 (point(s) of entry as a weak term) and #45
  (official evidence in the score, registry-corroborated positions, evidence pages
  in the brief) must merge before this document, because it describes them. #33 then merges into `main`. `docs/RUNNING.md` tells judges to clone the default
  branch.
- **Official evidence is only as good as the stored text.** Outside generation, a
  port reaches tier 1 or 2 only from a stored snippet (section 1); zones whose
  official pages were never fetched, or that have no page designating a port, stay
  at their registry tier. A stripped name can be a city ("Port of Hamilton" also
  matches "Hamilton"), so a city mentioned near "customs" on an official page can
  still ground; the committed sample snapshots were reviewed by hand.
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
| UN/LOCODE and WPI registries in Zetaris, evidence tiers | [#34](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/34) | `78afc7b`, `785ec5a`, `5a7fa93`, `8359a6d`, `01aebfe`, `c10f09b` |
| Reader context window, H-MEM label, SearXNG port, health probe | [#35](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/35) | `69d1a55`, `93609ca`, `dea81a2`, `af98049`, `f32764d`, `87769b5` |
| Stored official evidence, official-page snapshots, strong/weak entry terms, evidence UI | [#41](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/41) | `9403ef7`, `4114000`, `8a33d79`, `2081bc6`, `b368381`, `974da96`, `803066c` |
| "point(s) of entry" as a weak entry term | [#42](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/42) | `42d54df` |
| `pycountry` in the minimal install, warning when missing | [#44](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/44) | `d0f6b4f` |
| Official evidence in the score, registry-corroborated positions, brief sources, Benin example | [#45](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/45) | `e30ea65`, `a5698aa`, `47fd757`, `7f98ff9`, `0857c36`, `b29aaea`, `8932b76` |
| NemotronJudge advisory critic, frontend portKey parity, live recording of 25 October | [#47](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/47) | `164f740`, `9404cea`, `74f6299` and this update |
