# Zetaris and Meterless H-MEM

This note describes the sponsor integrations implemented for the hackathon. The
source branches are not all merged into `main` yet, so each section names its PR
dependency. Paths below are the implementation or test evidence for the claim.

## 1. Zetaris: data layer

**Depends on [PR #26](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/26).**

The one-off administrator SQL registers the public
[`seed/ports_of_entry.geojson`](../../seed/ports_of_entry.geojson) snapshot as:

- Lightning database `BLUE_INTEL_REST`;
- REST table `BLUE_INTEL_REST.poe_seed`, pointed at the raw GitHub GeoJSON;
- schemastore container `blue_intel`; and
- view `blue_intel.poe_ports`, which explodes the GeoJSON `features` array into
  one row per port and projects identity, location, validation, source and
  coordinate fields.

The seed contains 1,169 features. The setup script refuses a verification count
other than 1,169. Evidence: [`zetaris_setup_poe.sql`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/scripts/zetaris_setup_poe.sql),
[`zetaris_setup.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/scripts/zetaris_setup.py).

At runtime, `ZetarisClient.get_ports(zone_name=None, mrgid=None, limit=500)` reads
`blue_intel.poe_ports` through the Zetaris SQL REST endpoint and converts rows to
the evaluator's port shape. Text filters are UTF-8 hex encoded before they enter
SQL; `mrgid` accepts integers only. The sample path reads 20 real rows copied
from the same seed. Evidence: [`zetaris.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/app/adapters/zetaris.py),
[`poe_ports.json`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/data/sample/zetaris/poe_ports.json),
tests `test_get_ports_encodes_filters_safely`, `test_get_ports_normalizes_rest_cells`
and `test_sample_ports_end_to_end_with_evaluator` in
[`test_zetaris_adapter.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/tests/test_zetaris_adapter.py).

Every runtime query first passes a lexical read-only guard. It permits one
statement beginning with `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN` or `WITH`, and
rejects DDL/DML keywords outside string literals. The live client uses a 15-second
timeout and retries connection failures and HTTP 5xx twice, with 0.5/1.0-second
backoff. `SAMPLE_MODE=true`, or a missing `ZETARIS_API_KEY`, prevents network use.
Evidence: `dry_run`, `_live_rows` and `__init__` in
[`zetaris.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/app/adapters/zetaris.py),
plus the guard, retry and sample tests in
[`test_zetaris_adapter.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/tests/test_zetaris_adapter.py).

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
[`zetaris_setup.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/scripts/zetaris_setup.py).

## 2. Meterless H-MEM: cognition layer

**Depends on [PR #28](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/28).**

`backend/app/engines/hmem/` is a Python port of the Meterless H-MEM TypeScript
reference at upstream commit `1742dec56a66e58eef9dda2d2b865823758ca8cd`,
licensed Apache-2.0. It includes the deterministic 64-dimensional FNV-1a
embedder, exact hybrid retrieval weights/defaults, tiered store, model-free
mining with an optional synchronous model hook, conflict gate, sleep guardrails,
approval-only dreaming, and the 17 canonical trust-ledger actions. Evidence:
[`README.md`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/README.md),
[`embeddings.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/embeddings.py),
[`memory_retrieval.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/memory_retrieval.py),
[`types.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/types.py),
and the copied [`LICENSE`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/LICENSE).

The test fixture is byte-for-byte identical to Meterless's 13 official vectors
(SHA-256 `10afb5a07233466576ba6feb0d88408488909ba2721ee9157fdb932132917029`).
The parametrized test runs all 13 cases: record validation, feedback deltas,
ranking order, sleep guardrails, conflict gate, ledger audit and dream boundary.
Evidence: [`hmem_vectors.json`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/tests/fixtures/hmem_vectors.json)
and [`test_hmem_conformance.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/tests/test_hmem_conformance.py).

`recall_node` queries by normalized port name plus zone and attaches the top five
matches, including score, source and provenance, as `port["memory"]`.
`remember_node` writes one long-term memory per finalised port. A repeated verdict
gives the prior active memory `helpful` feedback. A changed verdict creates and
resolves a conflict: the previous record remains stored and receives
`supersededBy`; it is not deleted. Evidence: [`memory.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/agents/memory.py)
and tests `test_remember_then_recall_second_run`, `test_same_verdict_helpful` and
`test_verdict_flip_retains_old_and_audits` in
[`test_hmem_memory.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/tests/test_hmem_memory.py).

Working and long-term tiers are JSONL files under `HMEM_DIR` (default
`data/hmem/`); short-term records are memory-only. The separate `ledger.jsonl`
is append-only, validates all 17 action names, and stores previous/new snapshots
for audited mutations. Evidence: [`memory_store.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/memory_store.py),
[`trust_ledger.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/trust_ledger.py),
and `test_jsonl_persistence_and_ephemeral_tier` in
[`test_hmem_memory.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/tests/test_hmem_memory.py).

## 3. Agent flow and traces

**Depends on [PR #26](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/26),
[PR #28](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/28) and the
strict source check in [PR #29](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/29).**

The composed call order is:

```text
ZetarisAdapter -> HMemAgent (recall) -> EvaluatorAgent
  -> evaluate -> [prepare_retry -> evaluate] up to 2 times -> finalise
  -> HMemAgent (remember)
```

All nodes use the same `run_id`. By default they append JSONL to
`logs/trace-<run_id>.jsonl`; `TRACE_LOG_PATH` overrides the file and
`TRACE_STDOUT=0` suppresses stdout. Evidence: `ZetarisClient._trace` in
[`zetaris.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/app/adapters/zetaris.py),
`_write_trace` in [`evaluator.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/evaluator-followups/backend/app/agents/evaluator.py),
and `_trace` in [`memory.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/agents/memory.py).
The committed integration tests are `test_sample_ports_end_to_end_with_evaluator`
and `test_nodes_and_evaluator_share_trace` in the two test files linked above.

The following are selected, unchanged JSONL lines from a real sample-mode run on
2026-10-22. The run combined the calls made by those two committed integration
tests, selected the real seed fixture row `Port of Ghazaouet`, used an empty
temporary `HMEM_DIR`, and passed (`1 passed in 0.07s`):

```jsonl
{"timestamp": "2026-10-22T19:22:04.560147+00:00", "agent_name": "ZetarisAdapter", "run_id": "sponsor-e2e", "action": "zetaris_query", "input_summary": {"sql": "SELECT name, lat, lon, to_json(source_urls) AS source_urls, validated, geocode_source, zone_name, mrgid, id FROM blue_intel.poe_ports"}, "row_count": 2, "duration_ms": 0.382, "mode": "sample", "status": "ok"}
{"timestamp": "2026-10-22T19:22:04.560559+00:00", "agent_name": "HMemAgent", "run_id": "sponsor-e2e", "action": "recall", "input_summary": {"port_name": "Port of Ghazaouet", "zone_name": "Algeria"}, "memories": [], "handoff": {"from": "HMemAgent", "to": "EvaluatorAgent"}}
{"timestamp": "2026-10-22T19:22:04.563753+00:00", "agent_name": "EvaluatorAgent", "run_id": "sponsor-e2e", "action": "evaluate_port", "port_name": "Port of Ghazaouet", "input_summary": {"port_name": "Port of Ghazaouet", "retry_count": 0}, "verdict": "retry", "reasons": ["unknown source", "single extractor", "inside the EEZ", "no direct source (empty URLs or synthesis only)", "single geocoder, not cross-checked"], "retry_hint": "find an official source"}
{"timestamp": "2026-10-22T19:22:04.563820+00:00", "agent_name": "EvaluatorAgent", "run_id": "sponsor-e2e", "action": "prepare_retry", "port_name": "Port of Ghazaouet", "input_summary": {"port_name": "Port of Ghazaouet", "retry_count": 1}, "verdict": "retry", "reasons": ["unknown source", "single extractor", "inside the EEZ", "no direct source (empty URLs or synthesis only)", "single geocoder, not cross-checked"], "retry_hint": "find an official source", "handoff": {"from": "EvaluatorAgent", "to": "retry"}}
{"timestamp": "2026-10-22T19:22:04.564050+00:00", "agent_name": "EvaluatorAgent", "run_id": "sponsor-e2e", "action": "finalise_port", "port_name": "Port of Ghazaouet", "input_summary": {"port_name": "Port of Ghazaouet", "retry_count": 2}, "verdict": "flag", "reasons": ["unknown source", "single extractor", "inside the EEZ", "no direct source (empty URLs or synthesis only)", "single geocoder, not cross-checked", "unconfirmed after max retries"]}
{"timestamp": "2026-10-22T19:22:04.564687+00:00", "agent_name": "HMemAgent", "run_id": "sponsor-e2e", "action": "remember", "input_summary": {"port_name": "Port of Ghazaouet", "zone_name": "Algeria"}, "memory_id": "mem-1", "outcome": "created", "handoff": {"from": "EvaluatorAgent", "to": "HMemAgent"}}
```

The omitted JSONL lines are the second evaluation, second retry handoff and third
evaluation; they carry the same `run_id`. The retry bound and final conversion to
`flag` are tested in [`test_evaluator.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/evaluator-followups/backend/tests/test_evaluator.py).

## 4. Reproduce

Run from the branch named for each PR, or after all three PRs are merged. No
Zetaris or H-MEM test below needs network credentials unless `ZETARIS_LIVE=1`.

```bash
cd backend

# PR #26: adapter, guard, sample data and Zetaris -> evaluator integration
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_test POE_AUTO_REFRESH=0 \
  .venv/bin/python -m pytest tests/test_zetaris_adapter.py -v

# PR #28 + #29: 13 vectors, memory nodes and evaluator
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_test POE_AUTO_REFRESH=0 \
  .venv/bin/python -m pytest \
  tests/test_hmem_conformance.py tests/test_hmem_memory.py tests/test_evaluator.py -v
```

To isolate the credential-free e2e paths after the PRs are present together:

```bash
SAMPLE_MODE=true MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_test POE_AUTO_REFRESH=0 \
  .venv/bin/python -m pytest \
  tests/test_zetaris_adapter.py::test_sample_ports_end_to_end_with_evaluator \
  tests/test_hmem_memory.py::test_nodes_and_evaluator_share_trace -v
```

The live Zetaris tests require the local Zetaris instance and `.env` credentials:

```bash
set -a
source ../.env
set +a
SAMPLE_MODE=false ZETARIS_LIVE=1 \
  MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_test POE_AUTO_REFRESH=0 \
  .venv/bin/python -m pytest tests/test_zetaris_adapter.py -v -k live
```

Evidence for the live-test gate and assertions: `test_live_connection`,
`test_live_get_ports_for_zone` and `test_live_ports_end_to_end_with_evaluator` in
[`test_zetaris_adapter.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/tests/test_zetaris_adapter.py).
H-MEM is local and deterministic; it has no live-service test.

## 5. Limitations

- The 1,169-port GeoJSON is a repository snapshot, not current clearance advice;
  live Zetaris reads the REST table backed by that snapshot. The sample fixture
  contains only 20 rows. Evidence: [`zetaris_setup_poe.sql`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/scripts/zetaris_setup_poe.sql)
  and [`poe_ports.json`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/data/sample/zetaris/poe_ports.json).
- The setup is not idempotent and has no DDL rollback. It is an administrator
  command, never an agent action. Evidence: module docstring and `--apply` path in
  [`zetaris_setup.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/scripts/zetaris_setup.py).
- The SQL guard is conservative lexical validation, not a SQL parser or database
  permission boundary. The live Zetaris account should also be read-only.
  Evidence: `ZetarisClient.dry_run` docstring in
  [`zetaris.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/zetaris-adapter/backend/app/adapters/zetaris.py).
- H-MEM's default mining path is heuristic and model-free. The optional model
  hook is synchronous and is not used by `recall_node` or `remember_node`.
  Evidence: [`memory_mining.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/memory_mining.py)
  and [`memory.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/agents/memory.py).
- H-MEM tier files and the ledger are not a multi-file transaction. Dream
  proposals, conflict queues and sleep backups are instance-local. Evidence:
  [`README.md`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/engines/hmem/README.md).
- The memory node uses `fcntl.flock`, so its process lock is currently Unix-only;
  cross-platform locking remains a tidy-up item. Evidence: `_engine` in
  [`memory.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/agents/memory.py).
- The evaluator's official-source test is a hostname naming heuristic, not proof
  of government ownership and not an exhaustive government-domain allowlist.
  Evidence: `is_official_source` in [`evaluator.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/evaluator-followups/backend/app/agents/evaluator.py)
  and its true/false cases in [`test_evaluator.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/evaluator-followups/backend/tests/test_evaluator.py).
- These PRs provide the nodes and their tested call order, but do not add a
  LangGraph graph-construction file. H-MEM recalls are attached as evidence; the
  current evaluator does not consume them as clearance authority. Evidence:
  [`memory.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/hmem-engine/backend/app/agents/memory.py)
  and [`evaluator.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/evaluator-followups/backend/app/agents/evaluator.py).

## 6. Pre-existing and new code

The confidence formula and production write path are pre-existing:
`score_port()` and `apply_score()` in
[`backend/app/services/poe_confidence.py`](../../backend/app/services/poe_confidence.py).
The existing `backend/app/services/poe_*.py` pipeline is also pre-existing. The
evaluator imports those functions rather than copying or changing them; evidence:
[`evaluator.py`](https://github.com/Berry-Mappemonde/Blue-Intelligence/blob/evaluator-followups/backend/app/agents/evaluator.py).

The sponsor integration and evaluator files described above are new hackathon
work:

| Area | PR | New-work commits |
|---|---:|---|
| Evaluator node and trace/retry behavior | [#25](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/25) | `d8ae5fa`, `313733e`, `80362ca`, `139c751` |
| Strict official-source follow-up | [#29](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/29) | `bee620b` |
| Zetaris adapter, setup, fixtures and integration tests | [#26](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/26) | `45f61f7`, `2ac638f`, `1d3f908`, `72e32c4` |
| Meterless H-MEM port and memory nodes | [#28](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/28) | `eff8c67` |

