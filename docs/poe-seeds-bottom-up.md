# Bottom-up verification of Ports of Entry

## In plain language

We no longer start from a world map cut into zones (EEZs) to ask an
AI: “list every port of entry in this country.”

We start from what we have **already found**: the v1 map, previous world
runs, the Noonsite community listing, and OpenStreetMap. Each known place
becomes a **seed** — a record. On that record we keep every origin (who
saw it, under which name, with or without GPS, nearby OSM customs, etc.).
We do not flatten that into a single yes/no.

Then, for each record that is still doubtful, we do two things:

1. **TinyFish searches that place** — the port name, not the whole zone.
   Noonsite is excluded: we have already extracted that list.
2. **Claude reads the pages found** and answers only: *is THIS place an
   official Port of Entry?* Yes, no, or we cannot say.

Ports already cross-checked (listing + a run + coordinates) are not
touched again. The v1 map (`poe_ports`) is never overwritten automatically.

That is all. Inventory → targeted search → judgment. No world-wide
discovery, no canary on the hardest EEZs.

---

## Why we changed approach

The old (top-down) pipeline did, for each VLIZ EEZ:

web search of the zone → extract a list of ports → geocode.

The 12-EEZ canary was aimed exactly at the holes and the errors. It
measured the worst case, not the world. Relaunching a 6th world discovery
run reproduced the same noise, at the risk of polluting v1.

Existing sources already cover a large part of the listing (nearly half
after union, versus ~10% on the canary). What was missing was a
**single inventory** and **place-by-place verification**.

---

## Inventory: one seed = one place

### Identity

Key: VLIZ `mrgid` + normalized name (`dedup_key`, e.g. `8447:alofi`).
VLIZ is used to know **where** the port is, not to launch a zone crawl.

Matching is local to the EEZ (fuzzy + “Port of / Port de / (…)” aliases).
The same toponym in two EEZs remains two seeds.

### Sources (union, not intersection)

| Source | Collection / file | What it contributes |
|---|---|---|
| v1 map | `poe_ports` | Name, coords, URLs — **intact** |
| World runs | `poe_run_ports` | Versioned extracts (5 runs, 285 EEZs by default) |
| Noonsite listing | `backend/data/listing_control/all_countries.json` | Role `poe` or `other`, often without GPS |
| OSM cache | Mongo `osm_port_seeds` | Commercial harbours, `port_of_entry`, controls; marinas **only** if customs / border / PoE ≤ 800 m (`marina_pleasure`) |
| OSM priors | `backend/data/osm_port_priors.json` | Harbour / marina ≤ 800 m from customs or `border_control` |
| WPI | `backend/data/wpi_ports.json` | Commerce/industrial counter-list. Token `wpi_commercial`. **Never** PoE proof |

A seed seen only by v1, only by OSM, or only by the listing **stays** in
the union. We do not drop a name because another source does not know it.

Each merge adds an **observation** (origin, name seen, coords, tags).
We do not flatten listing / OSM / runs into an `is_poe` field.

### Verdicts (work triage, not official truth)

| Verdict | Rule | Action |
|---|---|---|
| `confirmed` | listing PoE ∩ (v1 \| run \| osm) **and** coordinates | GPS audited (homonyms). Re-geocode only `inland_far` / `ambiguous`, not the `ok` ones. |
| `probable` | OSM confidence ≥ 0.5, or ≥ 2 extracted sources, or listing ∩ extract without a point | Later, optional |
| `unverified` | A single extracted source + coords | Judge |
| `name_only` | Listing PoE without a point | Geocode, then judge |

A missing token (`osm:customs`, `listing:poe`…) means **unknown**, never
“false.”

### Collection

`POST /api/poe/seeds/build` rebuilds `poe_seed_ports` (delete + insert).
Does not touch `poe_ports` or `poe_run_ports`.

Each document carries at least:

- identity: `name`, `mrgid`, `zone_name`, `lat` / `lon`, `dedup_key`
- `seed_sources`, `observations`
- OSM / listing signals
- `verify_verdict`
- `search_query` — **this is what TinyFish must search**
- `search_exclude_domains`: `noonsite.com`
- `seed_line` — human summary of tokens, **not sent to Claude**

Atlas measurement of 2026-09-06 (v1 + 5 runs + listing + OSM priors, empty
OSM Mongo cache): **4027** seeds — 592 confirmed, 1805 probable, 1058
unverified, 572 name_only.

After the name_only run + unverified resume: 33 remaining `name_only`
(geocode failure). Review dossier: [`poe-name-only-33.md`](poe-name-only-33.md).

---

## Search: the seed drives TinyFish

For a seed to verify:

```
{name} official port of entry OR clearance OR "puerto habilitado" {zone}
```

Example: `Alofi official port of entry OR clearance OR "puerto habilitado" Niue`.

No listing/OSM token in the query (that would bias toward forums).

### Filters

1. **`exclude_domains=noonsite.com`** on the TinyFish Search API.
2. Client-side net: any `noonsite.com` URL is dropped before Fetch.
3. First pass: `include_domains` = the EEZ government whitelist
   (ISO2 / sovereign).
4. If zero official hits: same query **without** the whitelist, still
   without Noonsite.
5. Fetch: all whitelisted hits, cap 10, 150 URL/min.
6. Search: pagination (≤ 3 pages), 30 req/min PAYG, **one logical query
   per seed**.

The TinyFish Agent (lite then stealth) is called only if Fetch returns
`bot_blocked`, on **one** already-known official URL, 2 concurrent, credit
cap.

---

## Judgment: Claude reads the extracts, not the record

Claude receives only:

- the candidate name
- the VLIZ zone (name + ISO2)
- the extracts (Fetch pages, or Agent extracts, or failing that SERP snippets)

It replies in strict JSON:

```json
{"is_poe": true, "confidence": 0, "reason": "", "official_name": null, "kind": "pleasure"}
```

`kind` = `pleasure` | `mixed` | `cargo` | `other` | `unknown`.

- `true`: an **official** source designates **this** place as PoE / clearance
  / puerto habilitado **for pleasure craft** (yacht, recreational, pleasure
  craft) **or mixed** (commerce **and** pleasure stated explicitly).
- `false`: cargo-only, container terminal, industrial, airport, city,
  other country. A **marina is not** an automatic false: official
  clearance at **this** marina → `true`, `kind=pleasure`.
- `null`: extracts insufficient, or a designated port with no readable traffic.
- Deterministic net: `kind=cargo` (or commercial / freight / industrial
  aliases) forces `rejected`, even if the model set `is_poe=true`.

Escalation: Haiku → Sonnet if listing or `inconclusive` → OpenRouter on
failure or budget.

The `listing:poe` / `osm:customs` tokens **do not go** into the prompt.
Passing them would confirm Noonsite instead of reading the official source.

After judgment:

- `accepted` + listing + coords → may become `confirmed`
- `accepted` without listing → `probable`
- `rejected` → stays `unverified` (never promoted on its own)
- an existing `confirmed` is **never** demoted

Write: `poe_seed_ports` (source `seeds`) or `poe_run_ports` (versioned
run). **Never** `poe_ports`.

---

## Run sequence

```
POST /api/poe/seeds/build          inventory, 0 crawl
POST /api/poe/seeds/enrich         source=seeds
        name_only  → geocode → judge
        unverified → judge
        (probable optional)
```

Resume: skips `geocoded_at` / coords already present, and `judge_status`
already set.

Batches: `limit: 200` is possible. `limit: 0` = the whole requested verdict,
geocoding `name_only` first so the same record is not judged twice.

Forbidden for world discovery: `POST /api/poe/runs` with `limit: 0`,
`generate-batch` (410), `extract_ports` per EEZ via a map click.

Promotion to the map = **manual**.

---

## API

| Method | Route | Role |
|---|---|---|
| POST | `/api/poe/seeds/build` | Rebuilds `poe_seed_ports` |
| GET | `/api/poe/seeds` | Filterable read (`mrgid`, `verdict`) |
| GET | `/api/poe/seeds/line` | `search_query` + human summary |
| GET | `/api/poe/seeds/union` | Counts without persisting |
| POST | `/api/poe/seeds/verify` | Optional versioned run `poe_run_ports` |
| POST | `/api/poe/seeds/enrich` | Geocode + judge (`source=seeds` by default) |
| GET | `/api/poe/seeds/enrich/status` | Progress (`run_id=seed-enrich`) |
| POST | `/api/poe/seeds/enrich/cancel` | Stops seeds that have not yet started |
| GET/POST | `/api/poe/seeds/osm` | Overpass cache / refresh |

---

## Files

| File | Role |
|---|---|
| `backend/app/services/poe_seeds.py` | Union, verdicts, `search_query`, persistence |
| `backend/app/services/poe_seed_enrich.py` | Geocode, Search/Fetch/Agent, judge |
| `backend/app/services/osm_seeds.py` | Overpass cache v3 |
| `backend/app/core/tinyfish.py` | Paginated Search, `exclude_domains`, Agent |
| `backend/app/core/claude.py` | `complete_json_claude` (Haiku/Sonnet judge) |
| `backend/app/routers/runs.py` | Routes above |
| `backend/data/osm_port_priors.json` | 967 harbours/marinas near a control |
| `backend/scripts/run_seed_enrich_full.py` | Chains name_only then unverified |

---

## Invariants

1. No automatic upsert to `poe_ports`.
2. Listing = signal, not gold.
3. OSM = infra / prior, not designation (except `port_of_entry=yes` as a
   strong signal, not as a verdict on its own).
4. Noonsite absent from TinyFish searches.
5. One seed = one search = one judgment. Claude does not list other
   ports.
6. SERP hints without a list of port names (Niue / Mexico lesson).
7. Comparable versioned runs; manual map promotion.
