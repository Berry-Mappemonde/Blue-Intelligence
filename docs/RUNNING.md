# Running the PoE Reconciler

The agent product takes one maritime zone and returns its Ports of Entry, each with
a verdict, a confidence score, reasons and sources, plus a short brief for sailors.
It runs from a fresh clone with **no credentials and no MongoDB**.

```text
ZetarisAdapter → HMemAgent (recall) → EvaluatorAgent ⇄ ResearchAgent (retry, max 2)
              → EvaluatorAgent (finalise) → BriefingAgent (Meterless) → HMemAgent (remember)
```

## 1. Install (once)

```bash
git clone https://github.com/Berry-Mappemonde/Blue-Intelligence.git
cd Blue-Intelligence
python3 -m venv backend/.venv      # Python 3.12 or newer
# The agent pipeline needs only these six packages (pinned as in backend/requirements.txt):
backend/.venv/bin/pip install fastapi==0.110.1 httpx==0.28.1 pydantic==2.13.4 \
    python-dotenv==1.2.3 uvicorn==0.25.0 filelock==3.32.3
```

The full `backend/requirements.txt` is for the wider Blue Intelligence API. It
pins `torch==2.13.0+cpu`, which needs
`--extra-index-url https://download.pytorch.org/whl/cpu` on Linux and has no macOS
wheel. The pipeline never imports torch. For the tests, also `pip install pytest==9.1.1`.

## 2. Sample mode (no credentials)

```bash
backend/.venv/bin/python backend/run.py --input input_examples/01_bermuda.json
```

With no `.env`, `run.py` turns on `SAMPLE_MODE` and says so on stderr. Ports come
from the bundled Zetaris fixture (`backend/data/sample/zetaris/poe_ports.json`,
20 real ports from `seed/ports_of_entry.geojson`). The evaluator, retry loop,
H-MEM memory and briefing logic all run for real on that data; only the
Zetaris and model calls are replaced. The brief is then built deterministically
from the finalised ports (`llm.model = "caller-sample-fn"`).

Run the same input twice: the second run's `memory.recalled` is non-zero, because
H-MEM remembers the first run's verdicts (stored in `data/hmem/`, or `HMEM_DIR`).

Zones in the sample fixture include Bermuda, Angola, Azores, Alaska, Albania,
Anguilla, Argentina, Australia, Bahamas, Barbados, Belgium and Belize.

## 3. Live mode

```bash
cp .env.example .env    # then fill in the Zetaris and Meterless values
backend/.venv/bin/python backend/run.py --input input_examples/02_angola.json
```

Live mode needs `ZETARIS_API_KEY`, `ZETARIS_ORG_ID` and `METERLESS_RUNTIME_TOKEN`
(the Zetaris PoE view is registered once by `backend/scripts/zetaris_setup.py --apply`).
`NVIDIA_API_KEY` is optional. Every external call is bounded and falls back:

| Call | Bound | Fallback |
| --- | --- | --- |
| Zetaris SQL | 15 s × 3 attempts | bundled sample data, trace `status: "fallback"` |
| Nightshift probe | 3 s, cached 60 s | NVIDIA if configured, else sample brief |
| Nightshift / NVIDIA request | 90 s per provider (one retry inside it) | next provider, then sample brief |
| Whole run | 5 minutes | partial result with an `error` field |

`llm.provider` and `llm.model` in the output show which model actually wrote the brief
(the served model, as reported by the runtime).

**Recorded live run:** `output_examples/01_bermuda.live_nemotron.json` and its trace
`output_examples/01_bermuda.live_nemotron.trace.jsonl` were recorded on 22 October 2026
against a local Zetaris instance and Meterless Nightshift, with
`METERLESS_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b`. Nightshift served
`nvidia/nemotron-3.5-super-vl-120b-a12b` (`llm.provider: "nightshift"`). The trace
records both the requested and the served model, because the runtime may route a
request to a different model. Zetaris returned two Bermuda ports, and H-MEM
recalled memories from earlier local runs. It is a recording for reference: it
cannot be reproduced without credentials, and no code reads it.

## 4. CLI and HTTP

```bash
# CLI: JSON file in, JSON on stdout (and optionally a file)
backend/.venv/bin/python backend/run.py --input input_examples/03_azores.json --output out.json

# HTTP server on PORT (default 8000, host 127.0.0.1; set HOST=0.0.0.0 in a container)
backend/.venv/bin/python backend/run.py --serve
# in a second terminal:
curl -s localhost:8000/healthz
curl -s localhost:8000/zones
curl -s -X POST localhost:8000/run -H 'Content-Type: application/json' \
     -d '{"zone_name": "Bermuda", "run_id": "demo-1"}'
curl -s localhost:8000/runs/demo-1/trace
```

**Demo page:** with the server running, open <http://localhost:8000> in a browser.
Pick a zone, then press **Run verification**. The page shows the mode (live or
sample), whether Zetaris was live, and the LLM provider and served model, with a
"Nemotron via Nightshift" badge when the served model is a Nemotron model. It
also shows a card per port (verdict, confidence, reasons, sources, memories
recalled, research outcome), the brief, and an agent timeline built from the
run's trace (agents, actions, handoffs, retry rounds, durations). It is one
self-contained file, [`backend/app/pipeline/demo_page.html`](../backend/app/pipeline/demo_page.html),
with no external assets, so it works offline.

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Demo page |
| `POST /run` | Run the pipeline for one zone (JSON in, JSON out) |
| `GET /zones` | Zones available now: live Zetaris, or the sample fixture (`mode`: `live`, `sample` or `fallback`) |
| `GET /runs/{run_id}/trace` | Trace events of the latest run with that `run_id`, as JSON |
| `GET /healthz` | Health and whether `SAMPLE_MODE` is on |

If port 8000 is already in use, the server exits with "address already in use", and
`curl` would reach whichever program holds the port. Start it with another port,
for example `PORT=8001 backend/.venv/bin/python backend/run.py --serve`, and use
`localhost:8001` in the `curl` commands and the browser.

Input: `{"zone_name": str, "run_id": optional str}` (`run_id`: letters, digits, `_`, `-`).
Output: `run_id`, `zone`, `mode` (`live` or `sample`), `ports` (name, verdict,
confidence, reasons_en, sources with provenance `zetaris` or `hmem`,
memories_recalled, research), `summary`, `brief`, `llm`, `components`, `retries`,
`memory`, `trace_file`, `timings_ms`, `error`. Examples: `input_examples/` and
`output_examples/` (generated by running the commands above in sample mode).

## 5. Traces

Every agent writes JSONL events with the same `run_id` to stdout and to
`logs/trace-<run_id>.jsonl` (override with `TRACE_LOG_PATH`; `TRACE_STDOUT=0`
silences stdout). Agents: `RunPipeline`, `ZetarisAdapter`, `HMemAgent`,
`EvaluatorAgent`, `ResearchAgent`, `BriefingAgent`, `MeterlessGenerator`.
Handoffs are recorded in `handoff`; retries appear as `prepare_retry` events and
ResearchAgent `research_port` outcomes. `output_examples/*.trace.jsonl` are copies
of real traces from the example runs.

## 6. Tests

```bash
cd backend
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_test POE_AUTO_REFRESH=0 \
  .venv/bin/python -m pytest tests/test_run_pipeline.py -v
```

`test_run_pipeline.py` includes a fresh-clone simulation (`run.py` in a clean
environment). Live tests run only with `ZETARIS_LIVE=1` or `NIGHTSHIFT_LIVE=1`
and real credentials in the environment.

H-MEM serializes access with a file lock: `filelock` (installed above; Windows,
Linux and macOS). Without it, the lock falls back to `fcntl` (Linux and macOS), and
then to a thread-only lock that does not protect against other processes.
