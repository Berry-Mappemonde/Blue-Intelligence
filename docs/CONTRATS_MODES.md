# Mode contracts

**What I am trying to do.** Turn the living maritime web into a reliable geospatial base, laid on a worldwide map: action sites reachable by boat, official ports of entry, marinas, harbour offices, protected areas — without confusing a headquarters, an institutional page or a commercial harbour with what a pleasure-craft sailor needs.

The five modes were wired separately. Jobs that ask **the same question** do not use the same tools. This document reframes the pipelines around **7 families** (not 5: “qualification” must not become a catch-all), then names the twins to converge.

## What each mode seeks

| Mode | Contract |
| --- | --- |
| **Projects** | Find marine-conservation projects funded by foundations, extract the **action place** (one GPS per page, not the headquarters), keep only what is reachable by boat, score (S_ocean), write an isolated run — without emptying the live map. |
| **Ports of entry** | For **each VLIZ polygon** (`mrgid`, never a country), find the State page or PDF that lists pleasure-craft ports of entry, and write a GPS only if it falls inside *this* polygon. Top-down: polygon → list. Bottom-up: already-known place → evidence, and the whole catalogue if the page is one. Noonsite, OSM and the WPI are signals / counter-list, not evidence. Map publication = review / Gold. |
| **Marinas** | Worldwide `leisure=marina` directory (stable OSM identity), Google `/maps/place/` signal if it really exists, contacts and services **without inventing**. OSM anchorages apart, along the route. Isolated runs. |
| **Harbour offices** | Inventory the **offices** (the building, not the water body nor the marina), pull phone and VHF from them, without ever attaching them to marinas. |
| **MPA** | ProtectedSeas polygons on a **coastal stretch** (not the world), and **two distinct URLs**: manager (`manager_url`) vs visit / entry / permit / anchoring (`visit_url`). The visit is never the manager homepage. |
| **Science** | Locate oceanographic datasets from official catalogues (Sextant/SISMER, ODATIS, EDMED SeaDataNet), active Argo floats and CSR campaign tracks, each with the **direct link to its portal fiche**. EMODnet WMS layers as background (bathymetry, substrate, cables). Harvest by structured APIs (GeoNetwork JSON, SPARQL, ERDDAP) — never an LLM nor scraping. |
| **Climatology** | Serve a **versioned monthly atlas** (8-sector roses, Hs P50/P90, surface current, IBTrACS tracks) with `kind: "climatology"`, named period and DOI. Snapshot + API, **not a swarm**, not an LLM, not a forecast. `null` on land / NaN pixel / sample too thin. Blue Intelligence **shows** the atlas (7th mode); NAVIGUIDE **uses it** without painting it. |

Web-job legend: **P** Projects swarm · **TD** PoE top-down · **BU** PoE bottom-up · **MM** Marinas Maps · **ME** Marinas enrich · **CE** Harbour-office enrich · **AV** MPA visit.

OSM dumps (marinas, harbour offices, anchorages), MPA polygons, the Science harvest and Climatology snapshots do not chain the 7 families. That is not a hole: it is not the same object.

---

## 1. Search — where is the page?

| Job | Sentence | Tools today |
| --- | --- | --- |
| P | Discover project URLs on each listing | httpx + BeautifulSoup crawler on an **already-known MasterSeed**; TinyFish **Agent** if 0 URL |
| TD | Find the State URL that carries the list | SearXNG + Serper; TinyFish Search depending on variant; OpenRouter `:online` last |
| BU | Find the State page for this name | **`search_named`**: paginated TinyFish Search; `serp_filter`; DuckDuckGo if no key |
| MM | Open the Maps link and collect `/place/` | TinyFish **Fetch** of an **already-built** Maps URL; Search skipped |
| ME | Find a site if there is no OSM tag | **`search_named`**: TinyFish Search; `serp_filter`; DuckDuckGo if no key |
| CE | Find contact pages | **`search_named`** (same tooling); domain ranking afterwards |
| AV | Search visit `site:` then open web | **`search_named`**; DuckDuckGo if no key; no SearXNG |

## 2. Source filter — is this URL allowed to be read?

| Job | Sentence | Tools today |
| --- | --- | --- |
| P | Drop contact / donate / news from the listing | Path blacklist **in the crawler**, not `serp_filter` |
| TD | State domains + drop forums / OTA | ISO2 whitelist + `serp_filter` + SERP ML classifier |
| BU | Whitelist first, then without if 0 hit | `include_domains` in Search; `url_allowed`; **`serp_filter`** |
| MM | A nearby marina fiche, not a restaurant | Name / slug + 8 km |
| CE | Ignore networks / OTA | **`serp_filter`**; `_url_rank` ranking |
| AV | Homepage forbidden; Search hits judged | `serp_filter` **then** local score **then** `ask_yes_no` |

## 3. Read — what text do we have?

| Job | Sentence | Tools today |
| --- | --- | --- |
| P + TD | Extract pages and PDFs | **`read_url`** → `extract_cascade`: httpx, trafilatura ∥ Readability, PyMuPDF / Tesseract, Playwright, Jina ∥ TinyFish Fetch, Wayback |
| BU | Download the whitelisted hits | **`read_url(prefer_fetch=True)`**: Fetch, cascade if text unusable; Agent if `bot_blocked` |
| ME | Read the official site | **`read_url`** (cascade: PDF, HTML, Playwright) |
| CE | Download the contact pages | **`read_url(prefer_fetch=True)`**: Fetch, cascade if empty |
| MM | Read the rendered Maps page | TinyFish Fetch only (Maps JS DOM — outside the cascade) |
| AV | Read the `manager_url` | **`read_url(prefer_fetch=True, keep_if_links=True)`**; scoring **without** LLM |

P, TD, BU, ME, CE and AV go through `read_url`. MM stays Fetch-only (`/place/` fiche).

## 4. Content / object filter — is this the right object?

| Job | Sentence | Tools today |
| --- | --- | --- |
| P | Marine project, then reachable by boat | ML gatekeeper → `ask_yes_no` (`json` role, marine prompt); then `site_publishable` |
| TD | The “port” object comes out at extraction (the strong filter is the State source) | Catalogue parser / NER later |
| BU | Judge only the residue | `ask_yes_no` (`judge` role, pleasure-craft / cargo prompt) |
| Marinas dump | Pleasure-craft marina | Overpass `leisure=marina` |
| Harbour-office dump | Office, not water body | Overpass `office=harbour_master` (+ seamark / harbour) |
| Anchorages | Anchorage object | Overpass anchorage / named-bay tags |
| AV (Fetch) | Visit link in the HTML | Heuristic score, no judge |
| AV (Search) | Right visit page | `ask_yes_no` (`json` role, visit prompt); URL among the candidates |

P, BU and AV (Search) go through `ask_yes_no`. The OSM dump and the LLM judge are not the same implementation; the **question** is the same.

## 5. Structured extraction — which fields?

| Job | Sentence | Tools today |
| --- | --- | --- |
| P | Name, place, S_ocean, partners | NIM `extract` → OpenRouter → Claude; heuristic |
| TD | Port names (+ lat/lon in the text) | Catalogue parser first; NIM `extract` / `legal` ∥ spaCy; Claude last |
| ME | VHF, berths, draft, services, phone | **`run_page_enrich`**: tags; phone/VHF regex; NIM `page` → OpenRouter; Agent if official site |
| CE | Phone, VHF channel | **`run_page_enrich`** (same order); contact schema only |
| AV | Not domain fields: a URL | Links extracted from Fetch; no page JSON schema |

ME and CE are the “JSON on page text” twin (`page`). P and TD are the “domain JSON on a long corpus” twin (`extract`).

## 6. Geocoding — is this point in the right space?

| Job | Sentence | Tools today |
| --- | --- | --- |
| P | GPS of the action place | **`geocode_name`** Nominatim **∥** GeoNames; LLM tie-break if disagreement; haven ≤ 15 km (`site_publishable`) |
| TD | Glue the port into **this** polygon | **`geocode_port_dual`** (same parallel call); LLM tie-break; if both directories are mute: **`llm_geocode_port`** then in-EEZ / 15 km / 400 km river |
| BU | Geocode names without a point | **The same** `geocode_port_dual` + `llm_geocode_port` if mute + polygon filter |
| MM / dumps / MPA | — | GPS already in OSM / SHOM / NOAA / ProtectedSeas |

P and PoE share `geocode_dual` (Nominatim ∥ GeoNames). Space tests stay distinct: haven (`site_publishable`) vs VLIZ polygon (`classify_poe_point`).

## 7. Identity / duplicate — is it already there?

| Job | Sentence | Tools today |
| --- | --- | --- |
| P + TD | Merge two fiches of the same place | `same_site` (`app.core.dedup`): 500 m + 60% / 90% similarity |
| BU catalogue | Names already on the list: judge skipped | Identity **of a name in a catalogue**, not a GPS merge |
| Marinas dump | Upsert | `osm_id` |
| Harbour-office dump | Glue SHOM / NOAA onto OSM | `find_building`: 0.25 km, distance alone, no name |
| Anchorages | Corridor duplicates | name + geohash6 |
| MPA map | Do not re-download | 30-day tile cache (not an entity merge) |

---

## Real twins (to converge)

A twin, in this document, is not “two modes that should be merged”. It is two pieces of code that ask **the same question** — where is the page, what text do we have, is this the right object — and that, because they were written weeks apart, each reinvented their tools. Converging them is sharing the technical brick. It is not mixing the product contracts: a marina is still not a port of entry, a marine protected area is still not a conservation project.

Each of the six points below is a modification project. It first tells what the code does today, then why it is a real problem (and not only ugly code), then what we would change, and why that change is justified — including what we refuse to glue together.

### 1. Read a URL: one door, not five readers

As soon as we have a web address, we need the **text** of the page (or of the PDF). It is the same question everywhere. Yet the path is not the same depending on the mode.

The Projects swarm and the ports-of-entry top-down arm go through an extraction cascade (`extract_cascade`). We first download simply. If it is HTML, we extract the text. If it is a PDF, including a scan, we open it (and OCR it if needed). If the page is only JavaScript, we open a real browser. If the site blocks, we try a mirror. The ports-of-entry bottom-up arm, harbour-office enrichment, MPA visit-page search, and the marinas Google Maps job mainly call TinyFish Fetch: one shot, the rendered text, and that is all. Marina enrichment is even thinner: an HTTP download plus a readability extractor, without PDF or browser.

The problem is concrete. A State decree as PDF, opened by top-down, is read. The same decree, opened by bottom-up, can come back empty, because Fetch is not a PDF cascade. A marina site all in JavaScript passes the swarm (the local browser handles it) and fails marina enrichment. We therefore pay more on one side, or miss the information on the other, for an identical question: “give me the text of this URL”.

The proposed change is therefore a single door to read a URL. As soon as TinyFish Fetch does not return usable text — especially a PDF or a JavaScript site — bottom-up, marinas and harbour offices would enter the same cascade as Projects and top-down. We do not remove Fetch: it remains the right tool when we need the DOM after JavaScript, typically the Google Maps `/place/` fiche, which the cascade is not meant to parse like a decree. We also do not light the local browser on every successful Fetch: it only serves if simple HTML and Fetch have already failed. Otherwise the cost explodes, and we have gained nothing.

**Done.** Door `app.core.extract.read_url` / `read_urls`. Fetch first for BU, CE, AV. Cascade as soon as Fetch is empty. Chromium only after simple HTML and Fetch. Maps: Fetch only. `extract_cascade`: `%PDF-` magic, Content-Type / Content-Disposition; an error HTML under a `.pdf` URL is no longer a PDF.

### 2. Search “the official page of this name”: same tooling, distinct domain questions

Four jobs search the official page of an **already-named place**: a port, a harbour office, a protected area, a marina without a site in OpenStreetMap. It is the same human question. Each still has its own recipe.

Bottom-up has only TinyFish Search, filtered by a list of State domains. If there is no TinyFish key, there is no search at all. Harbour offices do TinyFish Search, then DuckDuckGo if it comes back empty, and drop Facebook or Tripadvisor with a small homemade list, instead of the search-result filter already shared elsewhere. MPAs do TinyFish Search, pass the results through that common filter (`serp_filter`), then a score, but have no DuckDuckGo net. Marina enrichment, if it has no site tag, hits DuckDuckGo and ignores TinyFish Search.

This is not the question of the ports-of-entry top-down arm. That one does not search “the page of *this* port”. It searches a **regulatory list for a whole exclusive-economic-zone polygon**. It therefore needs SearXNG, Serper, sometimes a model with web access. Gluing SearXNG onto a marina or an MPA would be the wrong tool: we are not looking for a ports-of-entry decree there.

The proposed change aligns only the **named** searches. We would start with TinyFish Search, pass the results through the same filter already used by top-down and MPAs to drop forums and classifieds sites, and keep DuckDuckGo only as a net when the TinyFish key is missing — exactly what harbour offices already do, and what bottom-up and MPAs do not have. Queries and domain lists would stay proper to each mode: a port of entry is not a protected-area permit page. We would change the tooling, not the domain question. We would not install SearXNG on marina, harbour-office or MPA enrichment.

**Done.** Door `app.core.search.search_named`. TinyFish Search first (paginated if the caller asks), then `serp_filter`. DuckDuckGo HTML only if the TinyFish key is missing — not a second opinion after an empty TinyFish. Queries, `include_domains` / `exclude_domains` and ranking stay proper to BU / CE / AV / ME. No SearXNG on these jobs. DDG net: `site:` operator + host filter so the whitelist survives without a TinyFish API.

### 3. Enrich a marina or a harbour office: the same step order, not the same form

The two enrichment jobs do the work closest to the repo: extract a phone, a VHF channel, sometimes services, **without ever inventing** a field. They already share the same NVIDIA model to read a page, OpenRouter with a credit check, DuckDuckGo, and the small HTML-read function. The TinyFish Agent is the last resort of both.

They still do not do the steps in the same order, and that is not justified by the domain. Harbour offices search the web immediately, because they often have no address in OpenStreetMap. Marinas first read the site tag, which is more economical when the tag exists. Harbour offices extract a phone number by a simple rule *before* calling a language model. Marinas call the model first and only look at OpenStreetMap tags at the end. The marina Agent can start from a URL found on DuckDuckGo, therefore sometimes a Tripadvisor. The harbour-office Agent only accepts an official site — and that second rule is the right one: an Agent launched on a review page invents or copies anything.

We would not merge the two data schemas: a marina has visitor berths and a draft, a harbour office only needs phone and VHF. What we would share is the **order** of the steps. We would start from the tags already there. We would search the web only if a URL is missing. We would read the page. We would extract by a simple rule what is trivial (a number, a channel). We would call NVIDIA then OpenRouter only if a hole remains. We would call the Agent only if the URL is really official. We would thus avoid paying a model to re-read a phone already in OpenStreetMap, and sending the Agent onto an engine result.

**Done.** Door `app.core.enrich.run_page_enrich`. Common order: tags → URL already there (`search_named` only if one is missing) → read → phone/VHF regex → NVIDIA `page` then OpenRouter if a hole remains → TinyFish Agent only if the URL is official (`serp_filter`, never an engine hit). Distinct schemas: marina = visitor berths, draft, services; harbour office = phone + VHF. A field already filled is not overwritten.

### 4. Say yes or no: one wiring, three different prompts

Three jobs say “I accept” or “I refuse” after seeing text or search results. Each has its own prompt and its own NVIDIA role. The Projects gatekeeper asks whether the page is a marine project. The bottom-up judge asks whether *this place* is a pleasure-craft port of entry, or cargo. The MPA judge asks, among a **list of URLs already found**, which one is a visit page — and it is not allowed to invent one. That last constraint is precious: it is what prevents hallucinating a visit address.

The problem is not that the domain questions are different. They must stay so. The problem is that each mode rewired the model call, the OpenRouter and Claude fallbacks, and the response format. When we fix a call bug — a timeout too short, a broken JSON, the Claude net — we fix it three times, or once.

The proposed change is a common adapter, not a single judge. We would send a prompt, and receive an object of the type “I accept or I refuse, optionally this URL among the candidates, here is why”. The three prompt texts would stay three texts. We would not write a “project or port or protected area” judge: that would be weaker than each specialist, and it would mix objects the product refuses to confuse.

**Done.** Door `app.core.judge.ask_yes_no`. NVIDIA → OpenRouter → Claude. `YesNo` response (accepted / refused / URL among the candidates / reason). Three prompts unchanged. Distinct NVIDIA roles: `json` (gatekeeper, MPA, without Flash) and `judge` (bottom-up, Flash last). A URL off the list or equal to `manager_url` is a refusal — that is the MPA anti-hallucination net, now in the adapter. `bool("false")` is no longer a yes. Not a single “project or port or MPA” judge.

### 5. Two nearby points: it is not always “the same object”

The marinas, harbour-office and anchorage dumps already share Overpass and the worldwide grid. There is no Overpass-unification project: that is already the case. The trap would be to glue onto it the Projects and ports-of-entry deduplication (five hundred metres and a close name).

When we merge two projects less than five hundred metres apart, we say: it is **the same action site**, we enrich a single fiche. When we glue a SHOM or NOAA point onto an OpenStreetMap object at two hundred and fifty metres, we say: two official maps speak of **the same building**, we superimpose a layer. It is not the same decision. Reusing the Projects deduplication for harbour offices would glue offices too far, or refuse a legitimate layer.

This point is therefore not a unification workshop. It is a **guardrail**. Same “identity” family in the taxonomy, two rules, two codes. We do not mix them.

**Done.** Doors `app.core.identity.same_site` and `app.core.identity.find_building`. `same_site` stays `app.core.dedup` (500 m + 60% / 90% similarity) — merge of Projects / PoE fiches. `find_building` is the 250 m overlay, distance alone, first nearest (no more last-wins), degree prefilter, radius read in `capitaineries.merge_km`. A different name does not prevent the overlay. A close name at 400 m does not glue two offices. No `is_duplicate` on harbour offices.

### 6. Geocode a name: one call to both directories, two space tests afterwards

Projects and ports of entry both ask Nominatim and GeoNames where a name is. Projects call them one after the other, then a language model if needed, then check we are at sea or in a haven less than fifteen kilometres away. Ports of entry call them in parallel, break ties with the model if they disagree, then require that the point fall inside **this** exclusive-economic-zone polygon — not “in France”, *this* VLIZ polygon.

The providers are the same, and the Nominatim / GeoNames disagreement is the same: that is why a single call “ask both, break ties if needed” is justified. What must not merge is the **space test** afterwards. A project does not have to enter a VLIZ polygon. A port of entry is not allowed to be glued onto Mayotte while we are filing metropolitan France. We would unify the geocoding tool, not the product geography.

**Done.** Door `app.core.geo.geocode_name` / `geocode_dual`. Nominatim ∥ GeoNames, `arbitrate_geocode` tie-break if disagreement, no third coordinate. `geocode_port_dual` reuses `pack_geocode_dual`. Projects: `site_publishable` (haven ≤ 15 km) in `apply_havre`; `llm_geocode` (conservation site) only if both directories are mute. PoE: VLIZ polygon unchanged; if both directories are mute, `llm_geocode_port` (port-of-entry prompt, not reef/MPA) then the same VLIZ test. An invented GPS outside *this* polygon is not written. No `classify_poe_point` on a project. No Project `llm_geocode` on a port.

### In which order, and why

We start with **read** (twin no. 1: **done**), because that is where bottom-up, marinas and harbour offices today lose PDFs and JavaScript pages, and because everything else — enrichment, judge — relies on a text already there. Then **named search** (twin no. 2: **done**), so harbour offices, MPAs, marinas without a site and bottom-up stop reinventing the net (TinyFish, the result filter, DuckDuckGo if the key is missing). Then the marina / harbour-office **enrichment order** (twin no. 3: **done**), which becomes simple once read and search are stable. The common **judge** (twin no. 4: **done**): one `ask_yes_no` wiring, three prompts. The **identity guardrail** (twin no. 5: **done**): `same_site` is not `find_building`. The **geocode** (twin no. 6: **done**): Projects reuse the ports-of-entry parallel call, without touching the haven rule.

We do not put SearXNG in marina or harbour-office enrichment: it is not a State list by economic zone. We do not replace Overpass with a web search for the dumps. We do not treat the MPA tile cache as a fiche merge. We do not launch the local browser on every TinyFish Fetch that already returned HTML.
