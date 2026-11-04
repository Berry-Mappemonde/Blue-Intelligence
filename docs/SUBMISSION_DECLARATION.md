# Pre-existing work declaration

For the Open Agent Hackathon 2026 submission form.

- **Cutoff:** 2026-10-22 00:00 UTC.
- **Rule:** a commit's **author timestamp** decides whether it is pre-existing or new
  (confirmed by the team lead, Clément Filisetti). Work authored before the cutoff is
  pre-existing, even if it was merged later.
- **Baseline:** `main` at `f613d03` (2026-10-18, the last commit before the cutoff),
  plus the two PR #24 commits listed in section 1.

Everything below comes from `git log` and the GitHub pull-request commit lists of
`Berry-Mappemonde/Blue-Intelligence`, as of 2026-10-25 (`feat/integrate-poe-pipeline`
at `ddc0123`, after PR #49). It covers `main`, the V2 integration branch
`feat/integrate-poe-pipeline` (the submitted branch) and every open pull request.

## How this was measured

- **Baseline.** The last commit on `main`'s first-parent line before the cutoff is
  `f613d03` (2026-10-18 17:57 UTC, merge of PR #16). That tree is the pre-existing
  baseline.
- **New files.** These are files present on `feat/integrate-poe-pipeline` or on an
  open PR branch but absent from `f613d03`. Each is attributed to the commit that
  first added it, and that commit to the pull request whose GitHub commit list
  contains it. PR #33 (V2 into `main`) is checked last, because its list includes
  everything merged into V2.
- **Times.** Git author times, converted to UTC. For every commit after the
  baseline, author and committer times are the same.
- **Authors.** Names are git author names:
  - `Geronimo` commits use Varun Gore's email.
  - `Clément`, `clement` and `Clément Filisetti` are Clément Filisetti.
  - `Hamid` is Hamid (HamidZ11).

Reproduce:

```bash
git log -1 --first-parent --before=2026-10-22T00:00:00Z origin/main            # baseline
git log --remotes=origin --not f613d03 --format='%h %aI %an %s'                 # author times after the baseline
git diff --name-only --diff-filter=A f613d03 origin/feat/integrate-poe-pipeline  # new files
git diff --numstat --diff-filter=MD f613d03 origin/feat/integrate-poe-pipeline   # changed pre-existing files
gh api repos/Berry-Mappemonde/Blue-Intelligence/pulls/<N>/commits --paginate     # PR attribution
```

## 1. Pre-existing work (before 2026-10-22 00:00 UTC)

Blue Intelligence existed before the hackathon. The repository has 659 commits up
to `f613d03`, the first on 2026-03-07.

| Git author | Commits before the cutoff |
| --- | --- |
| Cursor Agent (AI coding agent) | 388 |
| Clément Filisetti (incl. `NAVIGUIDE-for-Berry-Mappemonde`, `Berry-Mappemonde`) | 221 |
| emergent-agent-e1 (AI coding agent) | 44 |
| dependabot | 5 |
| Geronimo (Varun Gore) | 2 |
| Grok Bot | 1 |

The baseline contained:

- **Backend (FastAPI + MongoDB):** 116 files in `backend/app`.
  - The PoE pipeline: 14 `poe_*.py` services, including `poe_pipeline.py` and `poe_confidence.py`.
  - The LLM and search layer: `core/llm.py`, `core/nvidia.py`, `core/claude.py`, `core/extract.py`, `core/rag.py`, `core/search.py`, `core/tinyfish.py`.
  - 16 routers, including `routers/formalities.py` and `routers/health.py`.
- **Frontend (React map):** `frontend/src`, 89 files.
- **Data:** `seed/ports_of_entry.geojson` (1,169 ports) and `seed/projects.geojson`.
- **Infrastructure:** `infra/vps`, `infra/searxng`, and CI in `.github/workflows`.
- **Tests and scripts:** 83 test files in `backend/tests`; climatology and satellite scripts.

**Also pre-existing: two PR #24 commits.** They were authored before the cutoff and
merged into `main` after it (PR #24, merged 2026-10-22 14:42 UTC as `5eab301`):

| Commit | Author | Author time (UTC) | Subject |
| --- | --- | --- | --- |
| `8c071aa` | Geronimo (Varun Gore) | 2026-10-21 19:13:26 | "Bugs fixed #1" |
| `2113145` | Geronimo (Varun Gore) | 2026-10-21 20:21:49 | "fix(core): repair four logic defects and add regression tests" |

PR #24's other two commits are new work. Apart from these two, the only commits
outside the baseline that were authored before the cutoff are on the open Dependabot
pull requests #18–#23 (dependency bumps, 2026-10-19). Those are not merged into
`main` or the submitted branch.

## 2. New work (from 2026-10-22 00:00 UTC)

### Pull requests

| PR | Branch → base | Author | State (25 Oct) | What |
| --- | --- | --- | --- | --- |
| #24 | `fix/ci-test-and-dependency-hygiene` → main | Varun Gore | Merged 22 Oct | Logic fixes, CI flake, rule typing (2 of 4 commits new) |
| #25 | `evaluator` → main | Hamid | Merged 22 Oct | EvaluatorAgent: per-port checks, retry routing, JSONL traces |
| #27 | `feat/confidence-breakdown` → main | Varun Gore | Merged 23 Oct | Confidence breakdown behind every score |
| — | direct to main (`632ea01`) | Clément | 22 Oct | `infra/agents/` batch system |
| #26 | `zetaris-adapter` → main | Hamid | Open (in V2) | Read-only Zetaris REST client, setup script, fixtures |
| #28 | `hmem-engine` → main | Hamid (1 commit Clément) | Open (in V2) | Python port of Meterless H-MEM (Apache-2.0), recall/remember nodes |
| #29 | `evaluator-followups` → main | Hamid (1 commit Clément) | Open | Strict `is_official_source`, parallel-safe trace tests |
| #30 | `nightshift-generator` → main | Hamid | Open (in V2) | Nightshift-first generator, NVIDIA Nemotron fallback, sample mode |
| #32 | `run-pipeline` → main | Hamid (2 commits Clément) | Open (in V2) | `backend/run.py`, `POST /run`, orchestrator, sample inputs/outputs |
| #33 | `feat/integrate-poe-pipeline` → main | Clément (lead), Hamid | Open, WIP | V2: Nemotron suite, Zetaris and H-MEM in the existing PoE pipeline |
| #34 | `zetaris-registries` → V2 | Hamid | Merged 24 Oct | UN/LOCODE and World Port Index in Zetaris; evidence tiers |
| #35 | `phase1-fixes` → V2 | Hamid | Merged 24 Oct | Reader 40k window, H-MEM label, SearXNG port 8890, health probe |
| #36 | `feat/v2-ui-and-fixtures` → V2 | Clément (5 commits), Hamid (3) | Merged 25 Oct | V2 UI: registry-tier badges, Verify button, telemetry; fixture export |
| #41 | `evidence-storage` → V2 | Hamid | Merged 25 Oct | Stored official evidence, official-page snapshots, strong/weak entry terms |
| #31 | `sponsor-docs` → V2 | Hamid (2 commits Clément) | Merged 25 Oct | `docs/sponsors/SPONSOR_TECH.md` |
| #42 | `evidence-followup` → V2 | Hamid | Merged 25 Oct | "point(s) of entry" as a weak entry term (missed #41's merge) |
| #43 | `readme-v2` → V2 | Hamid | Merged 25 Oct | Judge-facing README section; `pycountry` in the minimal install |
| #44 | `pycountry-required` → V2 | Hamid | Merged 25 Oct | `pycountry` in the minimal install; one warning when it is missing |
| #45 | `tier-score-consistency` → V2 | Hamid (1 sync merge Clément) | Merged 25 Oct | Official evidence counts as an official source; registry-corroborated positions; evidence pages in the brief; Benin retry example |
| #46 | `feat/v2-ui-and-fixtures` → V2 | Clément | Closed 25 Oct, not merged | Superseded by #47; not part of the submitted branch |
| #47 | `v2-salvage` → V2 | Hamid | Merged 25 Oct | Advisory NemotronJudge (from #46, reworked); frontend `portKey` matching the backend |
| #48 | `v2-salvage` → V2 | Hamid | Merged 25 Oct | Live Bermuda run re-recorded (Zetaris, Mongo evidence, Nightshift Nemotron); NemotronJudge docs; judge reasons/excerpts in the trace |
| #49 | `seed-evidence` → V2 | Hamid | Merged 25 Oct | `seed_evidence_from_snapshots.py`: fill `poe_evidence` without regenerating |
| #50 | `submission-metadata` → V2 | Hamid | Open | `metadata.json`: machine-readable project summary |
| #37 | `fix/llm-reader-40k-context` → main | Varun Gore | Open | #35's reader-window fix, ported to `main` |
| #38 | `fix/hmem-remember-port-prefix` → `hmem-engine` | Varun Gore | Open | #35's H-MEM label fix, on `hmem-engine` |
| #39 | `fix/searxng-default-8890` → main | Varun Gore | Open | #35's SearXNG default, ported to `main` |
| #40 | `fix/health-unreadable-memory-not-degraded` → main | Varun Gore | Open | #35's health fix, ported to `main` (commit keeps Hamid as author) |

### New files, by first author

| PR | Author | Files |
| --- | --- | --- |
| #24 | Geronimo (Varun Gore) | `frontend/src/lib/__tests__/runRules.test.js` |
| #25 | Hamid | `backend/app/agents/__init__.py`, `backend/app/agents/evaluator.py`, `backend/tests/test_evaluator.py`, `logs/.gitkeep` |
| #27 | Geronimo (Varun Gore) | `backend/tests/test_poe_confidence_reasons.py`, `frontend/src/components/ConfidenceBreakdown.js` and its test |
| direct to main | Clément | `infra/agents/` (5 files); first added in `632ea01`, restored on the PR branches in `a461ac2` |
| #26 | Hamid | `backend/app/adapters/{__init__,zetaris}.py`, `backend/scripts/zetaris_setup.py`, `backend/scripts/zetaris_setup_poe.sql`, `backend/data/sample/zetaris/{connection,databases,example,poe_ports}.json`, `backend/tests/test_zetaris_adapter.py` |
| #28 | Hamid | `backend/app/engines/hmem/` (13 files, including the upstream `LICENSE`), `backend/app/agents/memory.py`, `backend/tests/fixtures/hmem_vectors.json` (official vectors, unmodified), `backend/tests/test_hmem_conformance.py`, `backend/tests/test_hmem_memory.py` |
| #28 | Clément | `backend/app/core/paths.py` (`6a93fe7`) |
| #30 | Hamid | `backend/app/core/generator.py`, `backend/tests/test_generator.py` |
| #32 | Hamid | `backend/run.py`, `backend/app/pipeline/{__init__,api,run_pipeline}.py`, `backend/app/pipeline/demo_page.html`, `backend/tests/test_run_pipeline.py`, `.env.example`, `docs/RUNNING.md`, `input_examples/` (3), `output_examples/` (8, one recorded live Nemotron run) |
| #33 | Hamid | `backend/tests/test_nemotron_suite.py`, `backend/tests/test_poe_integration.py` |
| #34 | Hamid | `backend/app/adapters/registry_sources.py`, `backend/app/agents/registry_check.py`, `backend/scripts/zetaris_setup_registries.sql`, `backend/data/sample/zetaris/{unlocode,wpi}_ports.json`, `backend/tests/test_zetaris_registries.py` |
| #35 | Hamid | `backend/tests/test_llm_context_window.py` |
| #36 | Clément | `backend/scripts/export_v2_fixtures.py`, `start_v2.sh` |
| #36 | Hamid | `frontend/src/components/poeRegistry.js` |
| #41 | Hamid | `backend/app/adapters/evidence_store.py`, `backend/tests/test_evidence_store.py`, `backend/data/sample/official_pages/` (README and 5 verbatim snapshots of official pages fetched on 25 Oct) |
| #31 | Hamid | `docs/sponsors/SPONSOR_TECH.md` |
| #45 | Hamid | `input_examples/04_benin.json`, `output_examples/04_benin.json`, `output_examples/04_benin.trace.jsonl` (`47fd757`) |
| #47 | Hamid | `backend/app/agents/poe_judge.py`, `backend/tests/test_poe_judge.py` (`9404cea`); `backend/tests/test_port_key_cases.py`, `frontend/src/components/__tests__/poeRegistry.test.js`, `frontend/src/components/__tests__/portKeyCases.json` (`164f740`) |
| #49 | Hamid | `backend/scripts/seed_evidence_from_snapshots.py`, `backend/tests/test_seed_evidence.py` (`4b6933c`) |
| #50 (open) | Hamid | `metadata.json`, `backend/tests/test_metadata.py` (`c2b6f1f`) |

PRs #42, #43, #44, #48 and #37–#40 add no files; they change files listed here or
pre-existing ones. #48 replaces the recorded live run in `output_examples/` (first
added in #32) with a recording made on 25 Oct.

### Pre-existing files changed during the hackathon

These files existed before the cutoff and were changed afterwards. Line counts are
`f613d03` → `feat/integrate-poe-pipeline`; open PRs are noted separately.

| File | Lines | Changed by |
| --- | --- | --- |
| `backend/app/services/poe_pipeline.py` | +213 −18 | Hamid, Clément |
| `backend/app/core/llm.py` | +106 −8 | Hamid, Clément |
| `backend/app/core/nvidia.py` | +35 −7 | Hamid, Clément |
| `backend/app/core/extract.py` | +50 | Hamid, Clément |
| `backend/app/routers/formalities.py` | +61 | Hamid, Clément |
| `backend/app/core/claude.py`, `backend/app/routers/health.py`, `backend/app/main.py` | +10 −6 | Hamid |
| `backend/app/config.py` | +2 −2 | Clément |
| `backend/app/services/poe_confidence.py`, `backend/app/core/run_rules.py`, `backend/app/core/geo.py`, `backend/app/services/climatology_cyclones.py`, `backend/data/run_rules.json` | +192 −11 | Geronimo (Varun Gore) |
| `frontend/src/components/ZoneFiche.js` | +203 −7 | Hamid, Clément, Geronimo |
| `frontend/src/App.js` | +73 −27 | Hamid, Clément, Geronimo |
| `frontend/src/i18n.js` | +66 | Hamid, Clément, Geronimo |
| `frontend/src/components/map/zonePopup.js`, `frontend/src/api.js`, `frontend/src/components/FormalitiesPanel.js` | +42 −6 | Hamid, Clément (Geronimo in `FormalitiesPanel.js`) |
| `frontend/src/components/Header.js`, `frontend/src/components/MapView.js` | +19 −20 | Clément |
| `frontend/src/components/ReviewView.js`, `audit/RulesPanel.js`, `lib/runRules.js`, `package.json`, `package-lock.json` | +19 −17 | Geronimo (Varun Gore), Clément (`package.json`) |
| `infra/searxng/*` (4 files) | +10 −9 | Hamid |
| Tests: `test_nvidia.py`, `test_health.py`, `test_searx_instances.py` (Hamid); `test_run_fingerprint.py` (Clément); `test_climatology.py`, `test_geocode_name.py`, `test_identity.py`, `test_ml_jobs.py`, `test_run_rules.py`, `infra/vps/ci/test_simulator_deploy_manifest.py` (Geronimo) | | |
| `README.md` | +166 | Hamid (#43, #48) |
| `.gitignore`, `docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` | small | Hamid, Clément; Geronimo |

Open PRs that change pre-existing files:

- #37: `core/claude.py`, `core/llm.py` and `core/nvidia.py`, on `main`.
- #39: `poe_pipeline.py` and `infra/searxng/*`, on `main`.
- #40: `routers/health.py`, on `main`.

## 3. Third-party code and data brought in during the hackathon

- **Meterless H-MEM reference** (Apache-2.0), ported to Python in
  `backend/app/engines/hmem/` with its `LICENSE`. The conformance vectors in
  `backend/tests/fixtures/hmem_vectors.json` are copied unmodified.
- **UN/LOCODE** (UNECE) and the **NGA World Port Index** (US Government, public
  domain). Only small fixtures are committed; the full datasets are downloaded by
  the admin setup into a gitignored folder.
- **Official-page snapshots** (#41): short verbatim excerpts of five government
  web pages, fetched on 25 Oct 2026: gov.bm, planning.gov.bm, customs.gov.ag,
  bahamascustoms.gov.bs and cbp.gov. Each keeps its URL, fetch time and the SHA-256
  of the full fetched text.

## Notes

- Open pull requests (#26–#30, #32, #33, #37–#40, #50) are listed under their PR. Their
  work is in the submission only where it is already on `feat/integrate-poe-pipeline`
  (#26, #28, #30 and #32 are fully in it through the V2 integration; #29 is, except
  for one commit).
- The pre-existing commits by Cursor Agent and emergent-agent-e1 were made with AI
  coding agents run by the team before the hackathon.
