# Review contracts by mode

The specification `docs/CAHIER_DES_CHARGES_REVIEW.md` v1.1 is the **PoE review contract**: one sheet per VLIZ polygon, every already-paid evidence, keep / discard choices, then **Gold**. The other modes have only a sketch there (§7.1, §7.3, §9.2, §11.1).

This document proposes the **same Review gesture**, adapted to each product mode. Review remains the **third tab** (Map / Console / Review): it opens the queue of the **active mode**.

Formalities is the **reference mode** (documents, not the ports; Propose; Gold lessons; extract after Gold). The other queues copy **the gesture**, not the object, not the `habilitados` / `jorf` tokens, not the EN·FR·ES filter. MPA / Projects have a Propose batch; marinas / harbour masters (Capitaineries) have a field judge **per sheet** (no OSM batch).

**Science** and **Climatology** have **no** Review queue in V1 (plan C8): harvest / snapshot, not a Gold run. The Review tab shows a placeholder there. This document does not cover them.

Inherits from: `docs/CAHIER_DES_CHARGES_REVIEW.md`, `docs/CONTRATS_MODES.md`, `docs/CAHIER_DES_CHARGES_POE.md`, `docs/CAHIER_DES_CHARGES_PROJETS.md`.

---

## 0. Meta-contract (common to all queues)

This section **prevails** as soon as there is a conflict with a UI or an implementation kind.

Review is a **review queue that results in a certified run**. It is not a map, not a crawler, not a silent goldiser.

| Rule | Meaning |
|------|---------|
| **One sheet = the object of the mode** | **Deduplicated** accumulation of v1 + **all** runs. Not a canary. Not a `run_id` as the Gold workspace. |
| **One sheet at a time** | Comment, choices (keep / discard), then Gold. |
| **Comment ≠ live** | Saving text does not write `projects` / `poe_ports` / `eez_zones` / `marinas` / `capitaineries` / `amp_sites`. |
| **Gold = entry into the certified run** | Explicit click. Feeds the mode’s Review run. Not `generate-batch`. Not a mutation on Save. **Does not display anything on Map by itself.** |
| **No Generate** | Out of Review. |
| **Isolated run = debug** | Useful to understand an engine. We do not goldise a canary / smoke / seed-enrich. |
| **Comment key** | `{mode}:{entity_id}` on the union sheet. No longer `{kind}:{run_id}:{id}` as the job key. |
| **Listing-control** | Stays in Console. Not a Review queue. |
| **Gold = the evidence, not the derived list** | We decide the document / the identity / the URL pair. We do not goldise 137 ports, nor each funder mention, nor the MPA polygon. |
| **Show all evidence** | The pipeline ranks; the UI hides nothing “to look clean”. A home page stays visible so we can discard it. |
| **“No evidence” is a decision** | UNCLOS / `none` (Formalities), `no_visit` (MPA), `unlocated` (Projects, **not** an invented GPS), “not a marina / not an office”. |
| **Propose ≠ Gold** | A judge (local ∥ LLM) may pre-fill. It overwrites checkboxes and comments. **It does not Gold.** It does not write live. |
| **Gold first, derived afterwards** | The snapshot freezes the evidence. A later job extracts / cleans **from that evidence only**. |
| **Pre-Gold = queue, not certificate** | “OSM has a point” ranks the sheet. It does not light Gold. |

**Test sentence.** A test that saves a comment and sees the live collection mutated **breaks the contract**. A test that clicks Gold and does **not** see the sheet in the certified run **also breaks the contract**. A test that clicks Gold and sees Map **change without** “Show the review” **breaks the contract**. A test where Propose lights Gold **breaks the contract**.

What changes by mode: **the question the reviewer decides**, **what counts as evidence**, **when Gold lights up**. The Map effect is **the same** for every mode (§8).

---

## 0.1 Formalities lessons — what we copy, what we do not copy

These rules come from the Formalities contract already in production (document Gold, vision judge, Propose batch, `review_lessons`). They **prevail** over a naïve copy of the `review_doc_picker.py` code.

### What we copy (gesture)

| Lesson | Meaning for the other queues |
|--------|------------------------------|
| **One question per mode** | Gold lights up when *that* question is decided, not when everything is checked. |
| **Grain of the object** | France hexagone ≠ Mayotte (`mrgid`). A project with n sites ≠ a world centroid. An office ≠ the marina 400 m away. An MPA = a `site_id` on **one** façade. |
| **Blacklist at path / object grain** | A useless `gob.mx` news item does not forbid the official PDF on the same domain. We blacklist a **path** or an `mrgid`, not an entire hostname by default. |
| **Local ∥ LLM, closed list** | The heuristic runs in parallel with the LLM. The LLM **invents no URL** outside the candidates already on the sheet. Vision is useful if the evidence is a page / a PDF; useless for an OSM tag. |
| **HITL** | Propose writes `review_suggest`. Gold writes `review_lessons` (keep/drop gap). The next batch rereads those lessons (few-shot + path score). The report says “Propose was wrong here” — **it does not write the rules**. |
| **Keys by `kind`** | `review_lessons` / `review_suggest`: `eez:`, `amp:`, `project:`, `marina:`, `capitainerie:`. Not a Formalities catch-all. |

### What we do not copy (Formalities business)

- Path tokens `habilitados`, `jorf`, `puertos` — each mode has **its** list.
- EN / FR / ES language filter of the Formalities Toloka / SERP pilot.
- `ports_ok` checkboxes / one click per derived object as a Gold condition.
- Automatic Gold because “the source looks official” (OSM ⇒ certified marina; all harbour masters (Capitaineries) `gold_on`).
- An LLM QA that **replays** Propose (same pages, same question) instead of auditing the human.
- Relaunching a crawl, SearXNG, or writing `poe_ports` / live “to see the map right away”.

### Order followed (already implemented)

1. **MPA** — same gesture “among these URLs, which is *the* evidence of *this* object”. Batch `scope=all`, keys `amp:`, `no_visit`.
2. **Projects** — two questions (project URL + `site_ok` site). Batch `scope=all`, keys `project:`. The judge refuses `snap_to_ocean` / HQ and invents no URL.
3. **Marinas / Harbour masters (Capitaineries)** — judge of **sourced fields** on **one sheet** (`scope=one`). `POST /review/suggest` `scope=all` → 400. Keys `marina:` / `capitainerie:`.

Infrastructure to **factor** (not the prompt): `TaskState` job + `GET /review/suggest/status`, `compare_verdicts`, few-shot by proximity (country / façade / sovereign), vision cascade already in `complete_json_cascade`, read-only report.

**Crowd / Toloka** (out of V1): if we delegate, we delegate **the same gesture** (are these links the right evidence of *this* object?), not the extraction of ports / sites / VHF. That does not enter this product contract.

---

## 1. Queue table

Five product modes, **five queues**. No separate `poe` queue (implementation accident: two Mongo collections). No country queue in place of an `mrgid`.

| Mode | One sheet = | Identifier | Evidence the reviewer judges | Gold when |
|------|-------------|------------|------------------------------|-----------|
| **Formalities** | one VLIZ polygon + its ports | `mrgid` | **State** URLs (TD all runs). WPI = counter-evidence. Noonsite off the sheet. | ≥ 1 TD kept (or UNCLOS `none`); ports extracted afterwards from the docs |
| **Projects** | one project (n sites) | `_id` or `url` | **Project page** URL + GPS of the action place visitable by boat | Project URL + ≥ 1 accepted site (not snapped / fallback / HQ) |
| **Marinas** | one marina | `osm_id` | OSM identity + basin GPS. Enrichment (VHF, berths, draught) **without inventing**. `/maps/place/` = signal. | Identity + GPS accepted. Enriched fields: keep only if they are sourced |
| **Harbour masters (Capitaineries)** | one **office** | `osm_id` and/or `shom_id` / `noaa_id` | Building (not the water body). Sourced tel + VHF (tags or official page). 250 m overlay ≠ 500 m merge. | Office + GPS accepted. Contact: keep only if it is not invented |
| **MPA** | one ProtectedSeas site (façade) | `site_id` | **Two** distinct URLs: `manager_url` ≠ `visit_url`. All visit candidates visible. | Pair decided: visit kept **distinct**, or “no visit” assumed |

---

## 2. Formalities — reference contract (already written)

This is `docs/CAHIER_DES_CHARGES_REVIEW.md` §3.4 / §7.2 / §11. We do not rewrite it. We **name** it so the other queues copy the gesture, not the object. Code state (reference, not to be copied word for word): `review_doc_picker.py`, `review_lessons.py`, `review_extract.py`.

**Question.** Among all TD already found for **this** `mrgid`, which one (or which ones) is *the* State list of **this** polygon? Gold freezes those documents. Ports are extracted afterwards from those URLs (not one click per name). Otherwise UNCLOS.

**Forbidden.** Country in place of the polygon. Separate ports queue. Hiding TDs “to keep only one”. Noonsite / wiki / forum as evidence. WPI as **positive** evidence of recreational use (except explicit mixed). Goldising a canary. Checking the ports as a Gold condition. Blacklisting an entire domain because one news item is useless.

**Review writes.** Comment; keep/drop **TD** (and pasted URLs) at `mrgid` grain; path pin / blacklist (ISO2 fallback); Gold = snapshot `{sources_td, ports: [], ports_status: pending_extract}` in the **certified run**. The extract job then fills `review_gold.snapshot` only — never `poe_ports`. Formalities Map remains the **unique run** as long as “Show the review” is unchecked.

**Propose (already there).** One click launches the batch on **all** Formalities sheets (`POST /api/review/suggest` `scope=all`). Overwrites checkboxes and comments. **Does not Gold.** On Gold: `review_lessons` compares the last proposal to your keep/drop. The next batch reinjects few-shot + path score. The report has a **“Propose was wrong here”** section.

---

## 3. Projects — proposed Review contract

Template: Projects spec v2 phase D + Review §7.1 / §11.1.

### 3.1 Object

One sheet = **one project**, union of v1 + `project_run_*` of the same project (`same_site`: 500 m + name). A world programme = **several sites** on **the same** sheet, not a “global” centroid.

### 3.2 Reviewer’s question

1. Is the URL a **project page** (not a foundation home, donate, news, jobs)?
2. Is each `sites[]` an **action place** precise enough and **accessible by boat** — not the headquarters, not an inland city, not a `snap_to_ocean`, not an `ocean_fallback`?
3. If there is no tenable site: `unlocated` (stays in the queue), **not** an invented GPS.

### 3.3 What we see on the sheet

| Element | Meaning | Forbidden |
|---------|---------|-----------|
| **URLs** | All project URLs, all runs, deduplicated, clickable | A single hidden URL; funder home presented as *the* page |
| **Funders** | Those of the page / the seed, merged | Inventing a funder |
| **Sites** | Name, GPS, `geo_source`, `site_ok`, textual evidence | A single HQ point; snapped left as-is |
| **Pipeline verdicts** | `snapped` / `fallback` / `hq_suspect` / `unlocated` / run↔v1 mismatch | Taking them as Gold without a click |

Input queues (spec phase D): `snapped`, `fallback`, `unlocated`, `hq_suspect`, run↔v1 mismatches. These are **filters of the same queue**, not five modes.

### 3.4 Choices

| Target | Actions | Rule fed |
|--------|---------|----------|
| URL | keep / blacklist (donate path, home) | `CRAWL_BLACKLIST` / project rules |
| Site | accept / reject / **edit GPS** (then Gold) | — |
| Whole project | Gold / leave in queue | Gold dataset gatekeeper |

Editing GPS **without** Gold: out of Review v1.1 scope (Review spec §21). Proposal: the edited GPS lives in `review_choices` until the Gold click.

### 3.5 Gold

**Active if**: at least one **project** URL kept **and** at least one accepted `site_ok` site (action-place GPS, not snapped / fallback / HQ).

**The click**: freezes URLs + accepted sites; writes the sheet into the **certified run** (`review_gold` kind `project`). Projects Map continues to display the **unique run**. The certified run appears only if “Show the review” is checked. Then used to recalibrate the gatekeeper (spec D2–D3) — **after** a Gold, not before.

**Does not**: goldise the whole run at once; republish an `ocean_fallback`; paste an MPA polygon as project evidence; remove a project from the map by default; goldise because the pipeline said `site_ok`.

### 3.6 What Review does not decide

Relaunch the swarm. Purge `projects`. Treat a funder as a project. Cross project ↔ PoE (out of spec scope).

### 3.7 What we copy from Formalities (implemented)

Propose batch `kind=project` (`review_project_picker.py`), **after MPA** (§0.1).

- **Judge’s question.** Among the URLs already on the sheet, which are a **project page**? Among the `sites[]`, which are a `site_ok` **action place** (not HQ, not snapped, not fallback)?
- **Closed list.** No invented URL. No invented GPS. `unlocated` stays in the queue.
- **Show everything.** All URLs, all sites, all pipeline verdicts — visible, not one URL “to look clean”.
- **HITL.** `review_suggest` kind `project`; lessons on Gold; few-shot priority same country / same funder; path score `donate` / `careers` / `news` / `jobs` (**Projects** list, not Formalities tokens).
- **After Gold.** Recalibrate the gatekeeper (spec D2–D3) from the report, **not** by writing `projects` from Propose.
- **Vision.** Useful (project page vs listing / donate). Same cascade as Formalities, different prompt.

---

## 4. Marinas — proposed Review contract

Template: Review §7.3 / CONTRATS_MODES “Marinas” / `REGLES_PARAMETRES` §3.3.

### 4.1 Object

One sheet = **one marina** (`osm_id`). Union of the unique run + enrichments. **Anchorages** (`marina_run_anchorages`, route corridor) are **not** this queue.

### 4.2 Reviewer’s question

Is this really a **visitable recreational marina** (`leisure=marina` basin), at the right GPS, **without** confusing it with a PoE or with the harbour master’s office next door?

Is the enrichment (VHF, visitor berths, draught, tel) **read** on a page / a tag, or invented?

### 4.3 What we see on the sheet

| Element | Meaning | Forbidden |
|---------|---------|-----------|
| OSM identity | `osm_id`, name / seamark tags | Merging two basins at the Projects `same_site` 500 m |
| GPS | OSM point of the basin | Snapping toward a customs, a PoE, a headquarters |
| `/maps/place/` | Signal (larger point) if it really exists | Inventing a Maps sheet; filtering the layer if absent |
| Website | OSM tag or Search named **official** | Tripadvisor / OTA as Agent enrichment source |
| Business fields | VHF, berths, draught, services — sourced | An LLM filling a hole by hallucination |
| Customs ≤ 800 m | Formalities **P seed**, outbound link | Evidence on the Formalities polygon sheet |

**No State URL required.** A marina is not a decree.

### 4.4 Choices

| Target | Actions |
|--------|---------|
| Identity / GPS | accept / “not a marina” (dry stack, restaurant, club ashore) |
| Maps URL / website | keep / blacklist (OTA, forum) |
| Each enriched field | keep / discard (empty ≠ false) |

### 4.5 Gold

**Active if**: OSM identity + GPS accepted.

**The click**: enters the sheet into the **certified run**. Marinas Map continues to display the unique run.

**Does not**: turn a marina into a PoE; attach the harbour master’s phone as a marina field without a source; goldise an anchorage; hide the unique run.

### 4.6 Code gap

`GOLD_KINDS` contains `marina`. `gold_pressed` ignores pre-Gold (Gold = override on). `is_pre_gold_marina` still ranks **the entire OSM dump with GPS** into the queue’s “pre-Gold” filter: that remains a **queue switch that is too wide**, not a certificate. The contract requires a **click** (identity + GPS seen). Do not reread “pre-Gold” as “already certified”.

### 4.7 What we copy from Formalities (implemented)

Field judge **per sheet** (`review_field_picker.py`). The object is an OSM point, not a State page. No world batch.

- **No world batch** on the entire OSM dump (cost, noise, different gesture).
- **Yes**: a small judge of **sourced fields** (VHF, berths, draught, tel) — keep the tag / the page, discard the hallucination. Closed list of fields already displayed.
- **“Not a marina”** = the UNCLOS equivalent (`dry stack`, restaurant, club ashore): a decision, not a silent Gold.
- **Blacklist**: OTA / Tripadvisor **by path**, not “all of `google.com`” because of a useful `/maps/place/`.
- Vision: of little use for OSM identity. No point copying the Formalities picker as-is.

---

## 5. Harbour masters (Capitaineries) — proposed Review contract

Product mode (README, CONTRATS_MODES). **Absent** from Review spec v1.1 (three modes). The UI already has `CapitainerieFiche`. `GOLD_KINDS` now contains `capitainerie`; Gold remains a **click**.

### 5.1 Object

One sheet = **one office** (the building), not the water body, not the marina. Identity: `osm_id` and/or SHOM / NOAA overlay at **0.25 km, distance only** (`find_building`). A different name does not prevent the overlay. A nearby name at 400 m **does not glue** two offices.

### 5.2 Reviewer’s question

1. Is the point the harbour-master **building**, not a pontoon, not a `leisure=marina`?
2. Do the telephone and VHF come from the **tags** or from an **official page** — not from a TripAdvisor review, not from an LLM invention?
3. Does the SHOM/NOAA overlay glue the **same** building (≤ 250 m) or have we merged two offices?

### 5.3 What we see on the sheet

| Element | Meaning | Forbidden |
|---------|---------|-----------|
| Sources | OSM, SHOM `CATSCF=6`, NOAA — **all** visible | Last-wins that erases an id |
| GPS | Building | Marina basin GPS “because it is next door” |
| Website | Official contact page | Social network / OTA |
| Tel / VHF | Regex tags → page → LLM only if a hole remains | Overwriting an OSM tag already filled |
| Marina link | **No attachment** | Copying `telephone_capitainerie` from the marina sheet as evidence |

### 5.4 Choices

| Target | Actions | Rule |
|--------|---------|------|
| Office | keep / “not an office” (water body, marina) | — |
| Overlay | accept the overlay / detach (two buildings) | Do not widen `merge_km` outside the interval |
| URL | keep / blacklist | `serp_filter` |
| Tel / VHF | keep / empty (suspect) | An empty field is better than a false one |

### 5.5 Gold

**Active if**: building identity + GPS accepted. Tel / VHF optional, but if they are displayed they must be **kept** (sourced).

**The click**: Gold kind `capitainerie`; sheet in the **certified run**. Harbour masters (Capitaineries) Map continues to display the unique run.

**Does not**: merge with a marina; reuse `same_site` 500 m; goldise without building GPS.

### 5.6 Code gap

`gold_pressed` no longer lights Gold by itself. `is_pre_gold_capitainerie` = building + GPS: **queue filter**, not a certificate. Check that no UI / API still defaults `gold_on: true` (former gap: all harbour masters certified without a gesture).

### 5.7 What we copy from Formalities (implemented)

Same field judge as marinas (`kind=capitainerie`): no world batch. SHOM/NOAA overlay accepted or discarded.

- **Field** judge (tel / VHF): sourced (tag, official page) vs invented / TripAdvisor.
- Overlay: accept or **detach** (two buildings). Do not widen `merge_km` because the judge “merged”.
- “Not an office” (water body, pontoon, marina) = `none` decision.
- No marina ↔ harbour master attachment as evidence.

---

## 6. MPA — proposed Review contract

Product mode. UI sheet already there (`AmpFiche`): `visit_candidates`, visit keep/drop, “no visit” checkbox. `GOLD_KINDS` contains `amp`. Propose + lessons kind `amp` (`review_amp_picker.py`).

### 6.1 Object

One sheet = **one ProtectedSeas site** (`site_id`) on one **façade** (not the world). Geometry = polygon already there. Review does not redraw the polygon. Review decides the **two URLs**.

### 6.2 Reviewer’s question

Among the candidates already found, which URL is the **visit** (permit, anchorage, entry, recreational) of **this** site — and which is only the **manager**?

The visit is **never** the manager homepage, nor a copy of `manager_url`, nor a URL off the list (`ask_yes_no` anti-hallucination).

### 6.3 What we see on the sheet

| Element | Meaning | Forbidden |
|---------|---------|-----------|
| `manager_url` | ProtectedSeas field (Website) | Taking it as *the* visit |
| **`visit_url` candidates** | All Search hits / Fetch links, **deduplicated, clickable** | Displaying only one “to look clean”; inventing one off the list |
| Pipeline statuses | `found` / `rejected_same_as_manager` / `not_found` / `none` | `found` while URL ≡ manager |
| LFP, designation, authority | Context | Gold criterion (LFP does not goldise) |
| Country / façade | Queue filter | A single world queue as truth |

Same spirit as Formalities TDs: **show everything, choose**. The pipeline proposes a rank; it is not a filter that hides.

### 6.4 Choices

| Target | Actions | Rule |
|--------|---------|------|
| `visit_url` | keep one among the candidates / discard homepages | Blacklist blog / generic anchorage **path** — not the entire domain of an authority |
| “No visit” | assume `not_found` / `none` | **Incomplete** Gold sheet or explicit “without visit” Gold |
| `manager_url` | correct if ProtectedSeas pasted a pipe of URLs | Never write manager into visit |

### 6.5 Gold

**Active if**: a `visit_url` **kept** and **distinct** from `manager_url`, **or** explicit confirmation “no visit page” (UNCLOS `none` equivalent on the Formalities side).

**The click**: snapshot `{manager_url, visit_url}` in the **certified run**. MPA Map continues to display the unique run. The ProtectedSeas polygon is not redrawn.

**Does not**: goldise the homepage; serve the 30-day tile cache as a sheet merge; launch SearXNG (this is not a State list per EEZ).

### 6.6 Code gap

Propose + `amp:` lessons + multi-kind report are in place. If a run does not write `visit_candidates`, the UI falls back to a single `visit_url` — the pipeline must **always** expose the list.

### 6.7 What we copy from Formalities (first queue to equip)

Closest gesture: “among these URLs, which is *the* visit of **this** `site_id`?”

- **Closed list.** Search / Fetch candidates only. Never `visit_url == manager_url`. Never a URL off the list (`ask_yes_no` anti-hallucination).
- **`no_visit`** = Formalities UNCLOS: Gold possible without a page.
- **Propose + HITL.** Same `TaskState` job / `GET …/status`; keys `amp:{site_id}`; few-shot by façade / country; path score homepage vs permit / anchorage / recreational (**MPA** list).
- **Vision.** Useful (permit page vs manager home).
- **After Gold.** Snapshot `{manager_url, visit_url}` only. No polygon redraw. No SearXNG from Review.
- LFP / designation = context, **not** a Gold criterion.

---

## 7. What Review does / does not do (by mode)

| | Formalities | Projects | Marinas | Harbour masters (Capitaineries) | MPA |
|---|------------|---------|---------|---------------|-----|
| Comment | yes | yes | yes | yes | yes |
| Choose URLs | TD + BU | project pages | website / Maps | contact page | visit candidates |
| Decides the object | State pages / PDFs (not each port) | sites keep/drop/edit GPS→Gold | marina vs not | office vs water body | visit vs manager |
| “No evidence” goldisable | UNCLOS / `none` | no (`unlocated` stays in queue) | “not a marina” | “not an office” | `no_visit` |
| Blacklist → rules | path / `mrgid` (not the entire domain) | listing paths | OTA (path) | OTA / networks | visit homepages (path) |
| Propose (judge) | **yes** (batch, does not Gold) | **yes** (batch, does not Gold) | **yes** (sheet, no OSM batch) | **yes** (sheet, no batch) | **yes** (batch, does not Gold) |
| HITL lessons / gap report | **yes** (`eez:`) | **yes** (`project:`) | **yes** (`marina:`) | **yes** (`capitainerie:`) | **yes** (`amp:`) |
| Relaunch a crawl | no | no | no | no | no |
| Invent a GPS / a URL | no | no | no | no | no |
| Write live without Gold | no | no | no | no | no |
| Change Map without “Show the review” | no | no | no | no | no |

---

## 8. Map and Review — a single switch

The **Map** tab has a **default** layer, independent of Review. Gold does not touch it.

The **unique run** will correspond to the test run we are about to launch.

| Mode | Default map |
|------|-------------|
| **Projects** | the unique run |
| **Formalities / PoE** | the unique run |
| **Marinas** | the unique run |
| **Harbour masters (Capitaineries)** | the unique run |
| **MPA** | the unique run |

Review constitutes **one human-certified run** (the goldised sheets, with their choices). It is one more run, the same object for every mode.

On Map, a **Show the review** button, unchecked by default:

- **checked** → the map shows the certified run of the active mode;
- **unchecked** → back to the default layer of the table above.

No “Formalities exclusive publication” regime. No “Projects skipper filter”. No “OSM badge”. One switch, five default layers.

---

## 9. Out of scope (these contracts)

- `poe` queue separate from the polygon sheet.
- Listing-control / Noonsite queue.
- **Anchorages** queue (Marinas corridor) — OSM dump, no enrichment; false positives = later.
- **Funders** queue (~861 portals) — Projects second deliverable, not a Review v1 queue.
- Split-screen run A \| run B comparator (replaced by the union).
- Skipper crowdsourcing from Review.
- Crawl relaunch from Review.
- SearXNG on marina / harbour master / MPA.
- Review / Gold of the **Science** and **Climatology** modes (C8).
- Copying the Formalities picker (tokens, prompt, EN·FR·ES filter) as-is onto another mode.
- LLM / crowd QA that **replays** Propose instead of auditing the human gesture.
- World Propose batch on the OSM marinas / harbour masters dump.

---

## 10. Minimal acceptance tests (when we implement)

1. Five queues, one per active mode. **Zero** “Ports of Entry” tab next to “Polygons”.
2. Comment persisted; live collections **unchanged**. Propose does not write live or Gold either.
3. Formalities: already the Review spec (all TDs, document Gold, extract afterwards, Propose batch, lessons). **Reference**, not a module to duplicate.
4. **Before any new Propose**: this page up to date (§0.1). Order: MPA → Projects → marinas / harbour masters field judge. Keys `kind:`.
5. Projects: Gold of a snapped project **refused** until the site is accepted; Gold of a `site_ok` project → sheet in the certified run; the unique run stays on Map.
6. Marinas / Harbour masters (Capitaineries) / MPA: Gold → certified run; the unique run remains the default map. Pre-Gold = queue filter.
7. Harbour masters (Capitaineries): no more default `gold_on: true`; Gold after building acceptance.
8. MPA: several visit candidates; Gold refuses `visit_url == manager_url`; `no_visit` goldises.
9. Map: “Show the review” checked = certified run; unchecked = §8 layer. Gold alone does not change Map.
10. Test sentence of §0 green for **each** kind — including “Propose does not light Gold”.

---

## 11. Documents

| Document | Role |
|----------|------|
| `docs/CAHIER_DES_CHARGES_REVIEW.md` | **Formalities / PoE contract** (queue, sheet, Gold). Prevails over “1 TD” of PoE spec §18. **Except** “Gold puts the accepted onto the map”: here Gold feeds the certified run; Map shows it only via **Show the review**. |
| `docs/CAHIER_DES_CHARGES_POE.md` | PoE object, VLIZ grain, D∩P, WPI. |
| `docs/CAHIER_DES_CHARGES_PROJETS.md` | Project object, phase D, snapped/fallback. |
| `docs/CONTRATS_MODES.md` | Five **pipeline** contracts (not Review). |
| `docs/REGLES_PARAMETRES.md` | Rules that Review choices must be able to **write**. |
| `docs/archives/PLAN_IMPLEMENTATION_FILIERES_CARTO.md` | Review / Gold = **control** stream; not a basemap. |
| This document §0.1 / §3.7 / §4.7 / §5.7 / §6.7 | What we copy from Formalities **before** writing a Propose elsewhere. |

## 12. Review report

The database already keeps everything: `review_comments` (key `{mode}:{entity_id}`), `review_choices`, `review_gold`, `review_suggest` / `review_lessons` **by kind**. The report (`GET /api/review/report`, **Report** button of the Review tab, JSON or Markdown export) aggregates these collections **read-only** to prepare pipeline improvements:

- **Proposed URLs**: any URL pasted in a comment (e.g. a PoE list of an EEZ polygon found by hand via Gemini) comes out at the top of the report — candidate for reading / retrieval by the pipeline on the next run.
- **Discarded**: TD, URLs, sites and discarded enriched fields — **path** blacklist candidates / engine fixes (not an entire hostname by reflex).
- **Gold**: certified sheets, with the date.
- **“Propose was wrong here”** (all kinds): keep/drop gaps, agreements, hints for the code. Matter for few-shot / tokens — **not** an automatic write of `_JUNK_PATH_TOKENS`.

The report writes nothing: neither a rule, nor a live collection, nor Gold. It is the raw material of a human decision.

---

In case of conflict on **eez vs poe**: one Formalities sheet.  
In case of conflict on **live write**: no live without Gold, no silent Gold, **no Gold by Propose**.  
In case of conflict on **what Map displays**: default layer of §8; the certified run only if **Show the review** is checked.  
In case of conflict on **what to copy from Formalities**: the gesture of §0.1, not the prompt nor the tokens.

*Any evolution of a Review rule is done first in the Formalities specification (`CAHIER_DES_CHARGES_REVIEW.md`) for PoE, and here for the other modes, then in the code.*
