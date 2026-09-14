# Specification — Review tab

Scoping document for the **Review feature** and the **Review tab** of Blue Intelligence.

It rereads the code (`review_queue`, `poe_zone_fiche`, `ReviewView`), the Formalities (PoE) and Projects specifications, PR #34 (7 September 2026), and the **Word review of 8 September 2026** (Berry-Mappemonde, 20 comments).

Written in plain language: it is the **contract** of what we are looking for, and what we refuse.

Version **1.1** — 8 September 2026. The Word corrections are traced in §22.

**Contents**

1. In one sentence
2. Why this tab exists
3. The contract
4. What we want to obtain
5. What we do not want
6. Vocabulary
7. The three queues (the three modes)
8. Multi-run Formalities sheet
9. Sheet contracts
10. Comment, motives, rules
11. Gold button
12. The code — where each piece lives
13. API
14. Data model
15. What the user sees
16. Who does what
17. Which workspace for the job
18. Current state and gaps
19. Acceptance tests
20. Risks
21. Out of scope
22. Trace of the review comments (Word 8 Sep)
23. Documents this specification inherits from

---

## 1. In one sentence

Reread **one sheet at a time**, in **one of the three modes** (Projects, Marinas, Formalities), see **all already-paid results deduplicated**, comment, **choose** the good evidence, **discard** the bad, then **Gold**: put the accepted sheet on the map.

---

## 2. Why this tab exists

The map and the Console **produce**. Review **judges**, then **publishes the accepted**.

The Formalities and Projects specifications require a **human reread** before any publication (§12 PoE: official list per polygon; Projects phase D: Gold). Without a dedicated screen, review remains a Mongo script or an overloaded map click.

The Formalities gesture: **one sheet per VLIZ polygon** (France hexagone ≠ Mayotte — **not** a “France” sheet nor a sheet per country), the Top-Down URLs **of all runs**, the **deduplicated PoE list**, the Bottom-Up URLs **per port**, **without a Generate button**. The same gesture, adapted, applies to a project and to a marina.

Blue Intelligence has **three modes**, not four: **Projects**, **Marinas**, **Formalities** (PoE + polygon **on the same sheet**). Review is the **third tab** (Map / Console / Review). It is not a fourth mode. The Review tab opens the queue of the **active mode**.

---

## 3. The contract

This section **prevails** over the UI, labels and implementations as soon as there is a conflict. For the Review screen, it also prevails over the PoE sentence “display only one TD URL”: in Review we **show everything**, we **choose**.

### 3.1 Object

Review is a **review queue that results in Gold**.

It is not a map. It is not a crawler. It is not a “silent goldiser” (saving a comment ≠ Gold).

A **sheet** = the object of the mode, **deduplicated accumulation of all runs** (plus v1), displayed **alone**, with a comment and **choices** (keep / discard).

### 3.2 Three queues = three modes

Not a kind `eez` beside a kind `poe`. Formalities = **one** queue, **one** sheet per polygon.

| Mode | One sheet = | Identifier | What we see there |
|------|-------------|------------|-------------------|
| **Projects** | one project | `_id` or `url` | v1 + `project_run_*` occurrences of the same project, deduplicated |
| **Formalities** | **one VLIZ polygon** (`mrgid`) | `str(mrgid)` | TD URLs of all runs + deduplicated ports + 1+ BU URLs per port |
| **Marinas** | one marina | `_id` | `marinas` (no `marina_run_*` today) |

**Why the v1.0 implementation separated `eez` and `poe`.** Two Mongo collections (`eez_zones` / `poe_ports`) produced two tabs. That is **not** a business rule. The Formalities reviewer judges **the polygon and its ports together**. A port without its polygon, or a polygon without its ports, is not the gesture.

No fifth “listing” queue. No country aggregate in place of an `mrgid`.

### 3.3 VLIZ grain (Formalities)

One Formalities sheet = **one polygon** (`mrgid`), never a country. France has 23 sheets. `France (hexagone)` ≠ `France (Mayotte)`.

The **rules** extracted from review (domains to keep, blacklist) are edited at polygon grain and can be **aggregated by sovereign** when it is the same law.

### 3.4 Formalities sheet — UI contract

For each `mrgid`, **without** a Generate button:

| Element | Meaning | Forbidden |
|---------|---------|-----------|
| **Top-Down URLs** | **All** State pages/PDFs already found for **this** polygon, **all runs combined**, **deduplicated**, **clickable** | Hiding one “to simplify”; a customs home without a list presented as *the* list; Noonsite; wiki; forum |
| **PoE list** | Ports attached to **this** `mrgid`, **all runs + v1 + seeds**, deduplicated by identity (`dedup_key` / name) | Country aggregate; one run that **replaces** the others |
| **Bottom-Up URLs per port** | State pages opened by searching **this** name, **all runs**, deduplicated, clickable | A single hidden URL; an orphan BU pile at zone level without a port |

The reviewer **selects** the best TD URL or URLs. They **deselect** those that miss the mark. The discarded ones go into the **blacklist** (domain and/or URL), memory for the crawl rules.

The same URL seen TD **and** BU = `from_arm = both` (gold source). EEZ with neither source nor port: `kind = none` + UNCLOS block if a code exists.

**WPI = inverse evidence.** WPI ports are **industrial fishing, industry or commerce**. A WPI hit is **not** a recreational PoE, **unless** it is **explicitly mixed** (a decree / catalogue that says so). WPI is never a sheet URL. Noonsite does not appear on the sheet.

### 3.5 Writes

| Write | When | Where |
|-------|------|-------|
| Comment | Save / navigation autosave | `review_comments` |
| Choice (URL kept, URL blacklist, port accepted / discarded) | Keep / discard click | review collections + **rules** (polygon grain, country aggregate) |
| **Gold** | **Gold** click on an accepted sheet | Gold set **and** map layer of the mode |

Saving a comment **does not touch** `projects` / `poe_ports` / `eez_zones` / `marinas`.

The **Gold** click is the **only** Review gesture that puts the accepted onto the map. It is not a `generate-batch`. It is not a silent mutation.

`generate` / `generate-batch`: **dead code to remove** from the product (routes already 410). They no longer appear in the Review contract.

**Test sentence, said simply.** A test that saves a comment, then sees `poe_ports` or `projects` changed **without** a Gold click, **breaks the contract**. A test that clicks Gold and sees **neither** Gold **nor** the map updated **also breaks the contract**.

### 3.6 Comment

- Free text from the first pass.
- **Recurring motives** (rotten TD, cargo port, wrong polygon…) are **detected while reviewing**. We will make structured verdicts **as we go**, not a frozen enum before having read 285 sheets.
- Comment key: `{mode}:{entity_id}` on the **multi-run** sheet (one thread per polygon / project / marina). A `run_id` is no longer the job key.
- Clearing the text and saving = empty comment (the green dot disappears).
- Persist before changing sheet or mode (button **and** autosave).

### 3.7 The job workspace = unique multi-run sheet

The UI label “Published map (v1)” is **misleading**. The job is not “reread v1 because it is published”. The job is: **one sheet that accumulates v1 + all runs, deduplicated**.

An “isolated run” selector may remain to **debug a pipeline**. It is **not** the Gold workspace. We do not goldise a canary.

### 3.8 Navigation

- One sheet visible. Previous / next. Keyboard arrows (outside a text field).
- Side list + filter (`q`).
- Pagination `offset` / `limit` (default 500, max 2000). The `total` is not lost.
- Counter `position / total`.

### 3.9 What Review decides / does not decide

| Review **does** | Review **does not** |
|-----------------|---------------------|
| Comment | Relaunch a crawl |
| Choose / blacklist URLs | Take Noonsite as evidence |
| Choose State pages / PDFs (not each port) | Overwrite v1 with a SERP batch |
| **Gold**: accepted sheet → Gold + map | Goldise in silence via “Save” |
| Feed the **rules** (blacklist, domains) | Invent a GPS |

---

## 4. What we want to obtain

Three deliverables, inseparable:

1. **The rereadable queue.**  
   Three modes, one complete **multi-run** sheet, a comment, a keyboard path. Volumes: ~4,465 projects, 285 polygons (ports **on them**), route marinas.

2. **The usable memory.**  
   Comments + choices + blacklist in a database from which we **edit rules** (polygon, then country). Not a disposable pad.

3. **The visible Gold.**  
   Sheets reviewed **and accepted** (**Gold** button) display on the mode’s map. That is the goal, not a side effect.

---

## 5. What we do not want

- A **Generate** / `generate-batch` / `force` button.
- A map write **without** a Gold click.
- A country in place of an `mrgid`.
- A “ports” queue **separate** from the Formalities polygons queue.
- Noonsite, wiki, forum as evidence. WPI as **positive** evidence of recreational use.
- Republishing a SERP run because the counter says 285.
- Confusing “Published map (v1)” and “published Formalities map”.
- A comment global to the run (the comment is **per sheet**).
- Polling the map while Review is open.
- Displaying the Swarm / Marinas / Formalities sidebars in Review.
- Hiding TD URLs “to keep only one” before the reviewer.

---

## 6. Vocabulary

| Word | Meaning here |
|------|--------------|
| **Review tab** | `view === "review"`, beside Map and Console (`audit`). |
| **Mode** | Projects \| Marinas \| Formalities. **Three.** Review does not add a fourth. |
| **Sheet** | **Deduplicated multi-run** view of a project, a polygon (+ its ports), or a marina. |
| **Queue** | Paginated list of the **mode**’s sheets. |
| **Displayable v1** | Today’s `projects` / `poe_ports` / `marinas`. Not a business publication. |
| **Isolated run** | `project_run_*` / `poe_run_*` snapshot. Useful to compare an engine, **not** to goldise. |
| **Comment** | Reviewer note. Repeated motives will become verdicts. |
| **Blacklist** | URL or domain discarded by the reviewer. Feeds the rules. |
| **Gold** | Sheet **accepted** by a human + State evidence (Formalities) or Projects criteria. **Displays on the map.** |
| **Gold button** | Explicit gesture: this sheet enters Gold **and** the map. |
| **Listing-control** | Noonsite control. Stays in Console. Not a Review queue. |

---

## 7. The three queues (the three modes)

### 7.1 Projects

Queue: title A–Z. Subtitle = funders or verdict.

Sheet: title, URL(s) of all runs, funders, place, GPS, `s_ocean`, category, `sites[]`, `snapped`. Run occurrences deduplicated on **the same** sheet.

Job: **project** URL (not a foundation home)? GPS = visitable action place? `snapped` / fallback = to note, excluded from Gold until accepted.

### 7.2 Formalities (polygon + ports)

Queue: disambiguated label (`zoneDisplayName`). Subtitle = sovereign. Extra: count of **deduplicated** ports.

Sheet: contract §3.4. **No** second “Ports of Entry” tab.

Job: among the clickable TDs, which one (or which ones) is *the* State list of **this** polygon? Gold on those documents. Ports listed by the runs are a preview. Gold extraction rereads only the kept URLs. Otherwise UNCLOS.

### 7.3 Marinas

Queue: `marinas` (as long as there are no marina runs).

Sheet: name, source, GPS, enrichment, VHF, berths, draught, harbour master's office, services, reviews.

Job: marina visitable along a route, **not** a PoE. A marina + customs ≤ 800 m = P seed on the Formalities side, not evidence on the polygon sheet.

---

## 8. Multi-run Formalities sheet

This is **simpler to review** than a 15-run selector.

| Layer | Source | On the sheet |
|-------|--------|--------------|
| Referential | `eez_zones` | label, UNCLOS, sovereign |
| v1 ports | `poe_ports` | in the list, marked v1 |
| Run ports | `poe_run_ports` **all** `run_id` of this `mrgid` | merged, deduplicated |
| Seeds | `poe_seed_ports` | BU URLs + candidates absent from v1 |
| TD | `sources` / `sources_td` of `eez_zones` **and** of **all** `poe_run_zones` of the `mrgid` | **all** clickable, deduplicated by URL |
| BU | `judge_sources` / `sources_bu` seeds + ports (all runs) | **per port**, all clickable |

The reviewer sees where each piece of evidence comes from (which `run_id`) **without** changing sheet.

The SERP world runs remain **stock to compare**, already **poured into the sheet**. We do not republish them as-is. 12-EEZ canaries = NO-GO as truth, but their URLs may appear: the reviewer discards them.

The `(285)` counter = VLIZ reference, not quality.

---

## 9. Sheet contracts (detail)

### 9.1 Formalities

- URL cleanup: `http` only; Noonsite / forums / magazines excluded from evidence.
- Dedup: one URL = one line; one port = one identity.
- **Proposed** rank (list/PDF page, `official`, `both`): this is a **sort**, not a filter that hides.
- WPI: “commerce / industry” badge = recreational **counter-evidence**, except explicit mixed.
- `wrote_poe_ports: false` until Gold has been clicked.

### 9.2 Projects / Marinas

Same spirit: deduplicated accumulation, reading until Gold. Project without URL: “No URL”. Marina: no State URL required.

---

## 10. Comment, motives, rules

```
review_comments
  _id        = "{mode}:{entity_id}"
  mode       = projects | formalities | marinas
  entity_id  = queue id
  comment    = text
  updated_at = ISO-8601
```

The queue exposes `has_comment` (green dot).

**Motives.** We do not freeze `accept` / `reject` / `edit-gps` before having read. When the same text comes back (“customs home”, “WPI cargo”, “wrong mrgid”), we **extract a rule** and, later, a clickable verdict.

**Rules.** Each keep / discard (URL, domain, port) is written into a **usable** database:

- grain = `mrgid` (and `iso2` / sovereign for the aggregate);
- type = `keep_td` | `blacklist_url` | `blacklist_domain` | `keep_port` | `drop_port`;
- serves the **next** crawl and the sheet (pre-checked).

Comment autosave: leave the sheet, change mode, Previous / Next, list click.

---

## 11. Gold button

We have talked about it: it is **in the contract**, not out of scope.

### 11.1 When it is active

On the current sheet, if the reviewer has enough to accept:

- Formalities: at least one TD URL **kept** (or URL pasted in the comment, or UNCLOS `kind = none` justified). Run ports are a preview, **not** a Gold verdict;
- Projects: project URL + accepted visitable site (not a `snapped` left as-is);
- Marinas: identity + GPS accepted.

Without that, Gold is **disabled** (or asks for explicit confirmation “incomplete Gold” — to be decided at implementation, default = disabled).

### 11.2 What the click does

1. **Freezes** the sheet: kept URLs, accepted ports, comment, timestamp, author if known.
2. **Writes Gold** (collection / export of the mode). This is not Noonsite. This is not a SERP run.
3. **Displays on the mode’s map** the accepted objects (Formalities ports, Projects sites, marina). Historical v1 **remains** in memory as a step; the layer **shown** to the skipper becomes Gold where a sheet has been goldised.
4. **Pushes the rules** (blacklist / domains / discarded ports) to the rules store.
5. Marks the sheet “Gold” in the queue (a dot distinct from a simple comment).

### 11.3 What the click does not do

- It does not overwrite the 285 polygons at once.
- It does not write if we have only typed a comment.
- It does not relaunch a crawl.
- It does not goldise a Noonsite listing.

We **approach** it as soon as Review + URL choices exist. The button is the **priority** gap of the current UI.

---

## 12. The code — where each piece lives

| Piece | Role today | 1.1 gap |
|-------|------------|---------|
| `app/routers/review.py` | GET/PUT comment | Gold + choices + blacklist |
| `app/services/review_queue.py` | 4 kinds, one `run_id` | 3 modes, union sheet |
| `app/services/poe_zone_fiche.py` | 1 TD displayed (`FICHE_TD_URL_CAP = 1`) | all TDs, clickable |
| `app/services/poe_zone_label.py` | France hexagone ≠ Mayotte | unchanged |
| `frontend/src/components/ReviewView.js` | 4 kind tabs + run selector | 3 modes; Gold; multi-select URLs |
| `ZoneFiche.js` | 1 TD + port list | all TDs + union ports |
| `PoeFiche.js` | separate ports queue | **to merge** into the polygon sheet |
| `Header.js` / `App.js` | Map / Console / Review | unchanged (tabs) |

Tests to extend: multi-run union, Gold does not write without a click, comment does not write the map.

---

## 13. API (1.1 target)

Prefix `/api`.

| Method | Route | Role |
|--------|-------|------|
| `GET` | `/review/queue?mode=&offset=&limit=&q=` | Queue of the mode (`formalities` = polygons) |
| `GET` | `/review/fiche?mode=&id=` | **Union** sheet + comment + choices |
| `PUT` | `/review/comment` | Text |
| `PUT` | `/review/choice` | keep / blacklist URL or port |
| `POST` | `/review/gold` | Gold + map, **one** sheet |
| `POST` | `/review/suggest` | **Propose** batch (`scope=all`): pre-fills all Formalities sheets. Does not Gold. |
| `GET` | `/review/suggest/status` | Batch progress |
| `GET` | `/review/report` | Comments, choices, Gold, **Propose / human gaps** |

An optional `run_id` on `fiche` remains allowed for a **filtered debug view**. Default = union.

`limit` bounded to `[1, 2000]`.

The current API (`kind=project\|eez\|poe\|marina`, `run_id`) is the v1.0 gap.

---

## 14. Data model

| Collection | Role |
|------------|------|
| `review_comments` | text, mode + id key |
| `review_choices` (target) | keep / blacklist, URL, port, `mrgid` |
| `review_gold` (target) | accepted snapshot + `golded_at` |
| rules (target, or `run_rules` / Formalities store) | domains / URLs / motives **editable by country / polygon** |

**Read** to assemble: `projects`, `project_run_projects`, `eez_zones`, `poe_ports`, `poe_run_zones`, `poe_run_ports`, `poe_seed_ports`, `marinas`.

**Written by Review**: comments, choices, Gold. **v1 map / `poe_ports` / `projects`: only via Gold**, object by object.

Indexes at boot (non-fatal): comments `(mode, entity_id)`; choices `(mode, entity_id)`; Gold `entity_id`.

---

## 15. What the user sees

**Header.** Map · Console · Review.

**Review.**

- Left: **mode** queue + filter.
- Top: the mode (already that of the app) · counter · Previous / Next · **Gold**.
- Centre: **one** union sheet. Formalities: **all** clickable TDs (keep / discard checkboxes) + deduplicated ports + BU per port.
- Bottom: comment + Save.

No fourth “Ports of Entry” switch beside “EEZ Polygons”.

EN / FR. Hint: *one sheet at a time; everything already found is there, deduplicated; Gold puts the accepted onto the map.*

---

## 16. Who does what

| Actor | They do | They do not |
|-------|---------|-------------|
| **Reviewer** | Scrolls, opens **all** URLs, chooses, comments, **Gold** | Crawler, empty the database, goldise Noonsite |
| **Operator** | Opens Review in the right mode; isolated-run debug if needed | Take a canary as truth |
| **Skipper** | Sees the **Gold map** where a sheet is goldised | Open Review |
| **Pipeline** | Feeds v1 and `*_run_*` | Write `review_comments` / Gold |
| **Review (code)** | Union + upsert comment / choices / Gold | Map mutation without Gold |

---

## 17. Which workspace for the job

**The union sheet (v1 + all runs, deduplicated).** Not “Published map (v1) because it is published”. Not `bestof3-v2` because the counter says 285.

An isolated run serves to **understand an engine**. Gold is decided on the union.

Canaries, `smoke-3-zones`, `seed-enrich`: out of truth. `example-official-sources`: sandbox of the gesture, not the world tour.

One comment thread per union sheet: we no longer lose notes when changing run.

---

## 18. Current state and gaps

### In place (PR #34)

Review tab, pagination, persisted comment, polygon sheet, no Generate, no map write on comment, map poll cut.

### Gaps — the 1.1 contract is not yet the UI

| Gap | Detail | Priority |
|-----|--------|----------|
| **Gold button** | Discussed, behaviour §11, **absent** from the UI | **P0** |
| `eez` ≠ `poe` queues | Implementation accident; business = **one** Formalities sheet | **P0** |
| Only one TD displayed | Show **all**, clickable, keep / blacklist | **P0** |
| Run selector as workspace | Union is the default; isolated run = debug | P1 |
| No persisted choices | `review_choices` + country / polygon rules | P1 |
| Structured verdicts | **Come as review goes** (motives), not a blocking gap | P2 |
| “Published map” label | Say “union / v1+runs” | P2 |
| `generate*` still in the repo | **Code to remove** (already 410) | P2 |
| Marinas without runs | OK as long as there are none | — |

---

## 19. Acceptance tests

1. Header: Map, Console, Review.
2. Review: no Swarm / Formalities sidebar.
3. Formalities mode: **285** polygon sheets; **not** a second queue of 1,280 ports.
4. Albania sheet: **several** clickable TDs if several runs found them; deduplicated ports; BU per port.
5. Deselect a rotten TD → blacklist; it does not come back as “best” on the next sheet of the same sovereign if the rule is aggregated.
6. Save a comment → `review_comments`; **`poe_ports` unchanged**.
7. **Gold** → Gold written + accepted ports **visible on the Formalities map**.
8. Next: another polygon; Albania comment / Gold unchanged.
9. Projects / Marinas mode: one sheet, no `/generate`.
10. ← → arrows outside the textarea.

Current tests: `tests/test_review_queue.py`, `tests/test_poe_zone_fiche.py` (to rewrite when union and Gold arrive).

---

## 20. Risks

| Risk | Counter-measure |
|------|-----------------|
| Overwrite v1 “to correct” without Gold | §3.5: comment ≠ map |
| Goldise Noonsite | Off the sheet |
| Reread a canary as truth | §17: union, then human choice |
| Lose comments when changing run | Key **without** job `run_id` |
| Timeout if we load all world `poe_run_ports` | Filter **by `mrgid`**; not a planet scan |
| Confuse marina and PoE | Separate modes; marina is not Formalities evidence |
| Hide TDs “to look clean” | §3.4: everything clickable |

---

## 21. Out of scope (1.1)

Listing-control queue in Review. *Split screen* run A \| run B comparator (replaced by the union). Skipper crowdsourcing. Crawl relaunch from Review. Free GPS edit without a Projects Gold pass. Second “ports only” mode.

**No longer out of scope:** Gold button, all TDs visible, unique Formalities sheet, blacklist → rules, map display of accepted sheets.

---

## 22. Trace of the review comments (Word 8 Sep 2026)

| # | Passage | Decision taken up |
|---|---------|-------------------|
| 0 | “one sheet per VLIZ polygon” | **Yes**: polygon, **not** a country / aggregated “per EEZ” sheet |
| 1 | “eez and poe are separate” / “there are only three modes” | **Three modes.** Formalities = PoE **on** the polygon sheet |
| 2, 3, 5 | 1 TD / PoE list / 1 BU | **All runs, deduplicated**, on **one** sheet |
| 4 | “WPI as evidence” | **Inverse evidence**: commerce / industry / fishing, except **explicit mixed** |
| 6 | Only one TD displayed | **All** visible; keep / **blacklist** |
| 7 | `review_comments` only write | Comments **and** choices in a database **to edit rules** (country / polygon) |
| 8 | `generate` / `generate-batch` | **Code to remove**; out of the Review contract |
| 9 | “A test that sees a v1 mutation…” | Reformulated §3.5: comment without Gold **does not** mutate the map; Gold **must** mutate it |
| 10 | “Free text” | **Yes** at the start; **motives** structure afterwards |
| 11 | “best among the runs” | **Display them all**, clickable |
| 12 | “Review does not goldise” | **Yes it does**: we **want** to goldise and **display** accepted sheets |
| 13 | `eez \| poe` | **Same sheet** per polygon |
| 14 | Sheet = `(kind, run_id, id)` | Sheet = **multi-run union** |
| 15 | “Gold does not exist yet” | We **approach** it; the button is missing |
| 16 | UI without Gold | **The Gold button is missing** |
| 17 | No structured verdict | **It comes as** review goes |
| 18 | No side-by-side comparator | **One multi-run sheet** instead |
| 19 | Gold out of scope | **In the contract**; behaviour §11 |

---

## 23. Documents this specification inherits from

- `docs/CAHIER_DES_CHARGES_POE.md` v1.4 — VLIZ grain, D∩P, §12, WPI counter-list. **Except** “display only one TD”: Review 1.1 shows all.
- `docs/CAHIER_DES_CHARGES_PROJETS.md` v2.0 — v1 treasure, phase D review / Gold.
- `docs/REGLES_PARAMETRES.md` — the rules that review must be able to **write**.
- `docs/ARCHITECTURE.md`, `docs/PRD.md`.
- `docs/CONTRATS_REVIEW_PAR_MODE.md` — same Review gesture for the five modes; Gold = certified run; Map via **Show the review**.
- PR #34 — first tab, comment API.

In case of conflict on **the grain** (country vs polygon), §3.3 prevails.  
In case of conflict on **a live write**, §3.5 prevails: no live without Gold, no silent Gold.  
In case of conflict on **what Map displays**, `docs/CONTRATS_REVIEW_PAR_MODE.md` §8 prevails: default layer of the unique run; the certified run only if **Show the review** is checked.  
In case of conflict on **eez vs poe**, §3.2 prevails: **one** Formalities sheet.

*End of the Review specification v1.1. Any evolution of a Formalities rule is done first here; the other modes in `CONTRATS_REVIEW_PAR_MODE.md`, then in the code.*
