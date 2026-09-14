# 33 `name_only` seeds — manual review dossier

Atlas snapshot of **2026-09-07** (`poe_seed_ports` collection, inventory
built on 2026-09-06T09:29:28Z, geocode on 2026-09-06 between 09:36 and 09:44Z).
Listing source: `backend/data/listing_control/all_countries.json`
(generated 2026-09-05T10:39:03Z, 1193 community PoEs).

This is **not** official truth. It is everything the system has on
these 33 records, plus the matches found in `poe_ports` (v1 map),
the other seeds, the listing, and the VLIZ EEZ index.

**Do not** rerun `POST /api/poe/seeds/build` after a correction: the build
empties `poe_seed_ports` and wipes judgments already made.

## Applied in Atlas (2026-09-07T05:53:15Z)

33/33 records written to `poe_seed_ports` only.
`poe_ports` remains **1280**. `wrote_poe_ports: false`.

| After | Count |
|---|---:|
| `poe_seed_ports` | 4034 (+7 splits) |
| `confirmed` | 781 |
| `probable` | 2157 |
| `unverified` | 1056 |
| `name_only` | 40 (33 sources + 7 listing+GPS children) |

Kiritimati: merge toward `8441:kiritimatiseaport` (Navy Harbour).
Saipan: GPS unchanged (15.16847). Marigot: GPS set on `8495:marinamarigot`.

---

## Why these 33 exist

A seed is `name_only` if the Noonsite listing says “PoE” **and** we
have **no** accepted point. Here, all 33 have:

| Field | Common value |
|---|---|
| `verify_verdict` | `name_only` |
| `listing_role` | `poe` |
| `seed_sources` | `["listing"]` only — neither v1, nor run, nor OSM at build |
| `has_coords` / `lat` / `lon` | `false` / `null` |
| `judge_status` | absent — Claude was not called |
| `osm_*` | empty (no OSM prior ≤ 800 m) |
| `source_urls` | `[]` |
| `search_exclude_domains` | `["noonsite.com"]` |
| `extraction_engine` | `seed` |
| `geocoded_at` | set — an attempt was made; `_needs_geocode` will skip them |

The `name_only` run geocoded 572 records: **537 ok**, **33 miss**. These 33
are the remainder. Relaunching enrich will not re-geocode them (`geocoded_at`
sentinel).

---

## How geocoding failed

The spatial filter (`classify_poe_point`) accepts a point only if it is
in **this** EEZ (`mrgid`), within ≤ 2.2 km (sliver), or inland ≤ 15 km from
the shoreline of this EEZ (or river exception ≤ 400 km if “harbour-like”).

| `spatial_kind` | n | Meaning |
|---|---:|---|
| `miss` | 26 | Nominatim/GeoNames returned nothing usable (often a compound “A / B” name) |
| `other_water` | 3 | Point at sea, outside the polygon — coords **found then discarded** (`lat`/`lon` stay null) |
| `inland` | 4 | Point too far inland, or wrong country — coords discarded |

The 7 spatial rejections have `geocode_arbitration: spatial_rejected`. The
system sometimes has an internal GPS, but it does not persist it.

---

## Synopsis table

| # | Listing name | Listing country | EEZ (`mrgid`) | Failure | Dist. | Duplicate / lead already in the database |
|---|---|---|---|---|---:|---|
| 1 | Geelong | Australia | Australia (8323) | ow | 3.4 | — |
| 2 | Newcastle and Port Stephen | Australia | Australia (8323) | miss | — | v1+probable `Newcastle` (Port Stephens separate) |
| 3 | Port Kembla / Shellharbour | Australia | Australia (8323) | miss | — | v1 `Port Kembla / Wollongong` |
| 4 | Big Creek / Placencia | Belize | Belize (8457) | miss | — | v1 `Big Creek`; `Placencia` probable |
| 5 | West End/Sopers Hole | British Virgin Islands | British Virgin Islands (8411) | miss | — | v1 `Soper’s Hole Dock / West End Ferry Terminal`; `West End` probable |
| 6 | Grand Mannan Harbour (Grand Manan Island) | Canada | Canada (8493) | miss | — | — |
| 7 | Marigot Bay (St Martin) | St. Martin | Collectivity of Saint Martin (8495) | miss | — | — |
| 8 | Oyster Pond - St Martin | St. Martin | Collectivity of Saint Martin (8495) | miss | — | — |
| 9 | Marina Los Morros | Cuba | Cuba (8406) | miss | — | — |
| 10 | Cassis | France | France (5677) | ow | 2.3 | — |
| 11 | Gironde Estuary & Bordeaux | France | France (5677) | miss | — | `Bordeaux` probable |
| 12 | Gulfe de Fos (Port St Louis, Port Napoleon, St-Gervais) | France | France (5677) | miss | — | — |
| 13 | Christmas Island/Kiritimati | Kiribati | Gilbert Islands (8488) | ow | 2529.9 | `Christmas Island Port` unverified |
| 14 | Tyrell Bay & Hillsborough (Carriacou) | Grenada | Grenada (8419) | miss | — | v1 `Port of Hillsborough` |
| 15 | Barbers Point Harbour (Ko Olina) | Hawaii | Hawaii (8453) | miss | — | — |
| 16 | Andaman Islands | India | India (8480) | inl | 697.8 | v1 `Port of Port Blair` on EEZ 8333 |
| 17 | Bandar Bintan Telani (BBT) – Bintan Island | Indonesia | Indonesia (8492) | miss | — | `Bandar Bintan Telani` probable; `Tanjung Pinang (Bintan Island, Riau Islands)` confirmed |
| 18 | Bowden Harbour/Port Morant | Jamaica | Jamaica (8459) | miss | — | — |
| 19 | Khuludhufushi | Maldives | Maldives (8345) | miss | — | — |
| 20 | Puerto Vallarta/ Banderas Bay | Mexico | Mexico (8429) | miss | — | v1 `Puerto Vallarta` |
| 21 | Colonia, Yap Island | Federated States of Micronesia | Micronesia (8316) | miss | — | — |
| 22 | Lele/Leluh Harbour | Federated States of Micronesia | Micronesia (8316) | miss | — | — |
| 23 | Tanapag Harbour (Saipan) | Northern Marianas | Northern Mariana Islands (48980) | miss | — | `Saipan` probable |
| 24 | Longyearbyen | Norway | Norway (5686) | inl | 520.2 | — |
| 25 | San Carlos - Vista Mar Marina | Panama | Panama (8423) | miss | — | — |
| 26 | Prince Edward Island | Marion & Prince Edward Island | Prince Edward Islands (8384) | inl | 13906.6 | — |
| 27 | Britannia Bay, Lovell | St. Vincent & the Grenadines | Saint Vincent and the Grenadines (8421) | miss | — | v1 `Mustique` |
| 28 | Lata, Ndendo Island (Santa Cruz Islands) | Solomon Islands | Solomon Islands (8314) | miss | — | `Lata` probable |
| 29 | Ria de Vigo and Baiona | Spain | Spain (5693) | miss | — | — |
| 30 | Cowes & R. Medina (Isle of Wight) | United Kingdom | United Kingdom (5696) | miss | — | — |
| 31 | Oban/Dunstaffnage | United Kingdom | United Kingdom (5696) | miss | — | — |
| 32 | Ketchikan | USA | United States (8456) | inl | 919.9 | v1+probable `Ketchikan Small Boat Harbor` **8463** ; `Ketchikan, Alaska` rejected on 8456 |
| 33 | Unalaska/Port of Dutch Harbor | USA | United States (8456) | miss | — | v1+probable `Dutch Harbor Small Boat Harbor` **8463** |


Failure legend: `miss` = no point; `ow` = `other_water`; `inl` = `inland`.

---

## Verification (2026-09-07)

Documented human review of the **33** `name_only` records. No Mongo write, no `POST /api/poe/seeds/build`, `poe_ports` intact.

Machine export: [`data/poe-name-only-33-verifications.json`](data/poe-name-only-33-verifications.json).

### Tally

| Action | n | Meaning |
|---|---:|---|
| `fusion` | 16 | v1/seed twin already there: do not recreate |
| `nouveau_point` | 10 | 1 real place, sourced GPS, no twin |
| `scinder` | 5 | The listing record glues 2 ports together |
| `corriger_zee` | 1 | Kiritimati: 8488 → **8441** + Navy Harbour GPS |
| `abandonner` | 1 | Prince Edward ZA: reserve, not a yacht PoE |
| `doute` | 0 | — |

Ketchikan, Dutch Harbor, Longyearbyen and Andaman are classed **fusion** (the target already carries the correct EEZ). The name_only stays on the wrong `mrgid`: abandon it, do not “correct” it in place.

### Table of the 33 decisions

| # | Name | Kind | Action | mrgid | Proposed GPS | Target / notes | Conf. |
|---|---|---|---|---|---|---|---|
| 1 | Geelong | 1 place | nouveau_point | 8323 | −38.1418881, 144.3621583 | Cunningham Pier ; FPOE DAFF commercial | high |
| 2 | Newcastle and Port Stephen | compound | fusion | 8323 | −32.9265876, 151.7839674 | → `8323:newcastle` ; Port Stephens ≠ FPOE | high |
| 3 | Port Kembla / Shellharbour | compound | fusion | 8323 | −34.480919, 150.9012821 | → Port Kembla / Wollongong ; Shellharbour ≠ FPOE | high |
| 4 | Big Creek / Placencia | 2 places | scinder | 8457 | 16.5203, −88.4104 / 16.5156, −88.3672 | → Big Creek + Placencia | high |
| 5 | West End/Sopers Hole | 1 place | fusion | 8411 | 18.3875292, −64.7033916 | → Soper’s Hole Dock | high |
| 6 | Grand Mannan Harbour | 1 place | nouveau_point | 8493 | 44.7633421, −66.7455097 | North Head Wharf (CBSA) | high |
| 7 | Marigot Bay (St Martin) | 1 place | fusion | 8495 | 18.0700053, −63.0884097 | → `8495:marinamarigot` + Fort Louis GPS ; ≠ St Lucia | high |
| 8 | Oyster Pond - St Martin | 1 FR/NL place | nouveau_point | 8495 | 18.0549308, −63.0155268 | Border bay ; listing PoE = FR side | high |
| 9 | Marina Los Morros | 1 place | nouveau_point | 8406 | 21.8999934, −84.9074329 | Cabo San Antonio ; ≠ Tazacorte | high |
| 10 | Cassis | 1 place | nouveau_point | 5677 | 43.2139518, 5.5360613 | Port de Cassis (sliver 2,3 km) | high |
| 11 | Gironde Estuary & Bordeaux | region | fusion | 5677 | 44.841225, −0.5800364 | → Bordeaux | high |
| 12 | Gulfe de Fos (…) | 2 ports | scinder | 5677 | 43.3758, 4.8316 / 43.4278, 4.9420 | Port Napoléon + Saint-Gervais | high |
| 13 | Christmas Island/Kiritimati | 1 place | corriger_zee | **8441** | 2.0075, −157.485833 | Navy Harbour ; ≠ AU 8309 ; ≠ Phoenix 8450 | high |
| 14 | Tyrell Bay & Hillsborough | 2 places | scinder | 8419 | 12.4833, −61.4568 / 12.4621, −61.4861 | Hillsborough v1 + Tyrrel Bay marina | high |
| 15 | Barbers Point (Ko Olina) | 1 complex | nouveau_point | 8453 | 21.3278642, −158.1196613 | KoʻOlina Marina ; EEZ 8453 already OK | high |
| 16 | Andaman Islands | region | fusion | **8333** | 11.6730477, 92.7460414 | → Port of Port Blair | high |
| 17 | Bandar Bintan Telani (BBT) | 1 place | fusion | 8492 | 1.1605006, 104.3201677 | → Bandar Bintan Telani ; Tanjung Pinang lat −3,36 suspect | high |
| 18 | Bowden Harbour/Port Morant | 1 place | nouveau_point | 8459 | 17.88718, −76.31667 | A single harbour (Bowden Wharf) | high |
| 19 | Khuludhufushi | typo | fusion | 8345 | 6.6233167, 73.0694663 | → Kulhudhuffushi Port (v1) | high |
| 20 | Puerto Vallarta/ Banderas Bay | city+bay | fusion | 8429 | 20.6561446, −105.243527 | → Puerto Vallarta ; ≠ Nuevo Vallarta | high |
| 21 | Colonia, Yap Island | 1 place | nouveau_point | 8316 | 9.5162421, 138.121629 | ≠ Colonia del Sacramento | high |
| 22 | Lele/Leluh Harbour | 1 place | fusion | 8316 | 5.3324023, 163.0241705 | → Lelu Harbor ; ≠ Okat | high |
| 23 | Tanapag Harbour (Saipan) | 1 place | fusion | 48980 | 15.22667, 145.73667 | → Saipan ; refine the quay | high |
| 24 | Longyearbyen | 1 place | fusion | **33181** | 78.22334, 15.64689 | → `33181:longyearbyen` already probable | high |
| 25 | San Carlos - Vista Mar | 1 place | nouveau_point | 8423 | 8.4823008, −79.9435075 | ≠ San Carlos MX | high |
| 26 | Prince Edward Island | not a PoE | abandonner | 8384 | — | ZA reserve ; Canada homonym | high |
| 27 | Britannia Bay, Lovell | 1 place | fusion | 8421 | 12.8760094, −61.1828409 | → Mustique | high |
| 28 | Lata, Ndendo Island | 1 place | fusion | 8314 | −10.7244151, 165.7982204 | → Lata | high |
| 29 | Ria de Vigo and Baiona | 2 places | scinder | 5693 | 42.2413, −8.7266 / 42.1185, −8.8451 | Vigo + Baiona (Galicia) | high |
| 30 | Cowes & R. Medina | 1 place | nouveau_point | 5696 | 50.7614678, −1.2966036 | Cowes Yacht Haven | high |
| 31 | Oban/Dunstaffnage | 2 places | scinder | 5696 | 56.4148, −5.4746 / 56.4499, −5.4325 | Oban North Pier + Dunstaffnage | high |
| 32 | Ketchikan | 1 place | fusion | **8463** | 55.3430696, −131.6466819 | → Ketchikan Small Boat Harbor ; 8456:ketchikanalaska already rejected | high |
| 33 | Unalaska/Dutch Harbor | 1 place | fusion | **8463** | 53.8831064, −166.552545 | → Dutch Harbor Small Boat Harbor | high |

### How to apply (without a rebuild)

1. **Never** `POST /api/poe/seeds/build` (delete+insert, judgments lost).
2. **Never** write into `poe_ports`.
3. **Merge**: note `review_target_dedup_key` on the name_only; optionally copy a `listing` observation onto the target. Do not duplicate the GPS onto a 2nd record. A `judge_status: rejected` without coords leaves `verify_verdict=name_only` (`apply_judge_verdict`).
4. **New point**: `$set` `lat`/`lon`/`has_coords: true`/`geocode_source: "manual_review"`. Do not clear `geocoded_at` if the manual GPS must stay (enrich would re-geocode).
5. **Correct EEZ**: `dedup_key` = `{mrgid}:{name}` is unique. Insert the new key, remove the old one. Useful overrides: Alaska **8463**, Line Group **8441**, Andaman **8333**, Svalbard **33181** (to add in `slug_overrides` for `norway`).
6. **Split**: abandon the compound name; attach or create one point per place.
7. **Abandon**: reason only, no GPS from the homonym.
8. `$set` examples: see the JSON. **Mongo was not modified** in this review.


---

## What is most worth doing by hand

The **verified** decisions are in [Verification](#verification-2026-09-07) (this A–D section was the initial hypothesis).

Three families, in ROI order.

### A. Merge (do not recreate a 34th port)

The listing has a **compound** name or a variant, and the place already exists
under another `dedup_key` (often v1 + `probable`):

| `name_only` record | Already in the database | Suggested action |
|---|---|---|
| Port Kembla / Shellharbour | `Port Kembla / Wollongong` v1+probable | Merge (Shellharbour = neighbour) |
| Big Creek / Placencia | `Big Creek` + `Placencia` v1+probable | Split / attach to both |
| West End/Sopers Hole | `Soper’s Hole Dock / West End Ferry Terminal` | Merge |
| Gironde Estuary & Bordeaux | `Bordeaux` v1+probable | Merge (or estuary office) |
| Puerto Vallarta/ Banderas Bay | `Puerto Vallarta` v1+probable | Merge |
| Bandar Bintan Telani (BBT) – Bintan Island | `Bandar Bintan Telani` probable | Merge |
| Tanapag Harbour (Saipan) | `Saipan` probable | Merge or pinpoint the quay |
| Lata, Ndendo Island (Santa Cruz Islands) | `Lata` v1+probable | Merge |
| Britannia Bay, Lovell | `Mustique` v1 | Merge (same island) |
| Tyrell Bay & Hillsborough (Carriacou) | `Port of Hillsborough` v1 | Merge Hillsborough ; Tyrell separate |
| Newcastle and Port Stephen | `Newcastle` v1+probable | Merge Newcastle ; Port Stephens separate |
| Ketchikan | `Ketchikan Small Boat Harbor` v1+probable **mrgid 8463** | Merge toward Alaska, not 8456 |
| Unalaska/Port of Dutch Harbor | `Dutch Harbor Small Boat Harbor` v1+probable **mrgid 8463** | Same |

### B. Correct the EEZ then re-geocode

The point is good, the **polygon** is the wrong one (listing slug → first
`mrgid` in `slug_overrides.json`).

| Record | Current EEZ | Probable EEZ | Evidence |
|---|---|---|---|
| Ketchikan | 8456 United States | **8463 Alaska** | v1 already on 8463 ; inland 920 km |
| Unalaska/Port of Dutch Harbor | 8456 United States | **8463 Alaska** | v1 already on 8463 |
| Christmas Island/Kiritimati | 8488 Gilbert Islands | **8441 Line Group** | listing group = Line Islands ; ow 2529 km |
| Andaman Islands | 8480 India | **8333 Andaman and Nicobar** | Port Blair v1 on 8333 ; inland 698 km |
| Longyearbyen | 5686 Norway (mainland) | Svalbard EEZ (absent from assignment) | listing group = Svalbard ; inland 520 km, geocoders agree |
| Barbers Point (Ko Olina) | 8453 Hawaii | 8453 OK | VLIZ iso2 null, not a bug |

`slug_overrides.json` maps `usa` → `[8456, 8463, 8453]` and `kiribati` →
`[8488, 8450, 8441]`. The listing build takes **one** mrgid; Alaska /
Line Islands ports fall on the first of the list.

### C. Near-miss spatial (2–4 km)

| Record | Kind | Dist. | Geocoders agree |
|---|---|---:|---|
| Cassis | other_water | 2.3 km | yes |
| Geelong | other_water | 3.4 km | yes |

The accepted sliver is 2.2 km. These two are just beyond it. A manual
GPS in the harbour, or a one-off relaxation, is enough.

### D. True orphans (human search)

No reliable v1/seed twin: Grand Manan (Mannan typo), Marigot Bay
and Oyster Pond (Saint-Martin, not Saint Lucia), Marina Los Morros,
Golfe de Fos (broken name), Ko Olina, Bowden/Port Morant, Khulhudhuffushi
(Khuludhufushi typo), Colonia Yap, Lelu/Leluh, Vista Mar Panama, Prince
Edward subantarctic (Canada homonym), Ría de Vigo & Baiona, Cowes,
Oban/Dunstaffnage.

---

## Homonym traps

| Do not confuse | With |
|---|---|
| Marigot Bay (Saint-Martin, 8495) | Marigot Bay Marina, Saint Lucia (8416) v1 |
| Prince Edward Island (8384, Marion SA) | Prince Edward Island, Canada |
| Christmas Island/Kiritimati (Kiribati) | Christmas Island (Australia) |
| Colonia, Yap | Colonia del Sacramento (Uruguay) v1 |
| San Carlos – Vista Mar (Panama) | San Carlos Baja / Sonora (Mexico) v1 |
| Ketchikan listing on 8456 | Ketchikan Small Boat Harbor on 8463 |

---

## Detailed records

### 1. Geelong

**Australia** · listing group `Victoria (Australia)` · `8323:geelong`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8323:geelong` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Australia / `australia` |
| Listing group | Victoria (Australia) |
| `mrgid` / `zone_name` | 8323 / Australia |
| VLIZ EEZ | Australia — Australian Exclusive Economic Zone (`iso2`=AU, `pol_type`=200NM, sovereign=Australia) |
| seed `country_iso2` | AU |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:36:16Z |
| `geocode_query` | `Geelong` |
| `spatial_kind` | `other_water` — point found but at sea outside the assigned EEZ → rejected |
| `distance_km` | 3.4 |
| `geocode_agree` | True |
| `geocode_arbitration` | spatial_rejected |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Geelong official port of entry OR clearance OR "puerto habilitado" Australia` |
| `seed_line` | `Geelong | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Geelong`, no GPS |

**Reading**

Nominatim and GeoNames agree (`geocode_agree: true`) but the point is 3.4 km outside the Australia EEZ polygon (`other_water`). Near-miss: the spatial filter discarded everything. Rerun geocode with a more precise name (Geelong Harbour / Port of Geelong) or accept a sliver > 2.2 km.


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8323** (unchanged 8323)
- GPS: **-38.1418881, 144.3621583** — Cunningham Pier (Geelong quay)
- Variant: -38.15, 144.366667 — Port of Geelong FPOE DAFF
- Sources:
  - Nominatim OSM way/node Cunningham Pier -38.1418881, 144.3621583 (2026-09-07)
  - DAFF First Point of Entry — Port of Geelong Determination 2019 (−38.15, 144.366667)
  - geocode_cache Nominatim Geelong, Australia −38.1493248, 144.3598241 (rejected other_water 3.4 km)
- Note: 1 city / 1 port. EEZ 8323 OK. The city geocode was discarded (sliver 3.4 km). DAFF: commercial + passenger FPOE, not non-commercial (yacht = prior permission). No v1/seed twin.

---

### 2. Newcastle and Port Stephen

**Australia** · listing group `New South Wales` · `8323:newcastleandportstephen`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8323:newcastleandportstephen` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Australia / `australia` |
| Listing group | New South Wales |
| `mrgid` / `zone_name` | 8323 / Australia |
| VLIZ EEZ | Australia — Australian Exclusive Economic Zone (`iso2`=AU, `pol_type`=200NM, sovereign=Australia) |
| seed `country_iso2` | AU |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:36:06Z |
| `geocode_query` | `Newcastle and Port Stephen` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Newcastle and Port Stephen official port of entry OR clearance OR "puerto habilitado" Australia` |
| `seed_line` | `Newcastle and Port Stephen | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Newcastle and Port Stephen`, no GPS |

**Reading**

Compound “A and B” name: the geocoder set nothing. On the same EEZ, the `Newcastle` seed already exists as `probable` (-32.9266, 151.7840) and in `poe_ports` v1. Port Stephens (listing spelling: Stephen) is a second place. Decide: merge with Newcastle, or create two points.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `2_lieux_listing_1_poe_officiel` · confidence: **high**
- Correct mrgid: **8323** (unchanged 8323)
- Merge target: `8323:newcastle`
- GPS: **-32.9265876, 151.7839674** — Newcastle (v1 + probable)
- Variant: -32.7218138, 152.1440889 — Nelson Bay / Port Stephens (anchorage, not a DAFF FPOE)
- Sources:
  - poe_ports v1 Newcastle −32.9265876, 151.7839674 mrgid 8323
  - DAFF FPOE Port of Newcastle (−32.933333, 151.766667) — non-commercial allowed
  - DAFF seaport-locations : Port Stephens et Shellharbour absents
- Note: Compound name. Newcastle = real PoE (v1 + DAFF non-commercial). Port Stephens (~45 km, Nelson Bay) is not a DAFF First Point of Entry: do not create a 2nd PoE. False friend Port Kennedy (WA / Torres) already noted.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Newcastle | displayed on map | -32.9265876, 151.7839674 |
| `poe_seed_ports` | Newcastle | probable | -32.9265876, 151.7839674 |

`Port Kennedy (Thursday Island and Horn Island)` matched by tokens (`port`): **false friend** (WA coords 115.75°E, not NSW). Ignore.

---

### 3. Port Kembla / Shellharbour

**Australia** · listing group `New South Wales` · `8323:portkemblashellharbour`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8323:portkemblashellharbour` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Australia / `australia` |
| Listing group | New South Wales |
| `mrgid` / `zone_name` | 8323 / Australia |
| VLIZ EEZ | Australia — Australian Exclusive Economic Zone (`iso2`=AU, `pol_type`=200NM, sovereign=Australia) |
| seed `country_iso2` | AU |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:36:09Z |
| `geocode_query` | `Port Kembla / Shellharbour` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Port Kembla / Shellharbour official port of entry OR clearance OR "puerto habilitado" Australia` |
| `seed_line` | `Port Kembla / Shellharbour | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Port Kembla / Shellharbour`, no GPS |

**Reading**

Compound A / B name. v1 and a `probable` seed already carry `Port Kembla / Wollongong` (-34.4809, 150.9013). Shellharbour is a neighbouring town, not the same quay. Probable merge with Port Kembla / Wollongong, or a distinct point at Shellharbour.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `2_toponymes_1_poe_officiel` · confidence: **high**
- Correct mrgid: **8323** (unchanged 8323)
- Merge target: `8323:portkemblawollongong`
- GPS: **-34.480919, 150.9012821** — Port Kembla / Wollongong (v1 + probable)
- Variant: -34.5788697, 150.8672489 — Shellharbour (town, ~13 km, not a DAFF FPOE)
- Sources:
  - poe_ports v1 Port Kembla / Wollongong −34.480919, 150.9012821
  - Nominatim harbour Port Kembla −34.46346, 150.90148
  - DAFF FPOE Port Kembla (−34.466667, 150.9) — commercial + passenger, not non-commercial
- Note: Shellharbour is the neighbouring town / Shell Cove marina, not a distinct FPOE. Merge toward Port Kembla / Wollongong. Do not split a 2nd PoE.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Port Kembla / Wollongong | displayed on map | -34.480919, 150.9012821 |
| `poe_seed_ports` | Port Kembla / Wollongong | probable | -34.480919, 150.9012821 |

---

### 4. Big Creek / Placencia

**Belize** · `8457:bigcreekplacencia`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8457:bigcreekplacencia` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Belize / `belize` |
| Listing group | — |
| `mrgid` / `zone_name` | 8457 / Belize |
| VLIZ EEZ | Belize — Belizean Exclusive Economic Zone (`iso2`=BZ, `pol_type`=200NM, sovereign=Belize) |
| seed `country_iso2` | BZ |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:36:43Z |
| `geocode_query` | `Big Creek / Placencia` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Big Creek / Placencia official port of entry OR clearance OR "puerto habilitado" Belize` |
| `seed_line` | `Big Creek / Placencia | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Big Creek / Placencia`, no GPS |

**Reading**

Two Belize ports already in v1 and as `probable`: Big Creek (16.5203, -88.4104) and Placencia (16.5156, -88.3672). The listing record glues two places together. Do not recreate: merge or split.


**Verification** (2026-09-07)

- Decision: `scinder` · kind: `2_lieux` · confidence: **high**
- Correct mrgid: **8457** (unchanged 8457)
- Targets: `8457:bigcreek`, `8457:placencia`
- GPS Big Creek (`8457:bigcreek`): **16.5203083, -88.4103792** (v1 + poe_seed_ports probable)
- GPS Placencia (`8457:placencia`): **16.5156113, -88.3671785** (poe_seed_ports probable)
- Sources:
  - poe_ports v1 Big Creek 16.5203083, −88.4103792
  - poe_seed_ports Placencia probable 16.5156113, −88.3671785
- Note: Two Belize ports (~4 km). The listing record glues both. Attach the listing to the two existing seeds; do not create 8457:bigcreekplacencia as a 3rd point.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Big Creek | displayed on map | 16.5203083, -88.4103792 |
| `poe_seed_ports` | Placencia | probable | 16.5156113, -88.3671785 |
| `poe_seed_ports` | Big Creek | probable | 16.5203083, -88.4103792 |

---

### 5. West End/Sopers Hole

**British Virgin Islands** · listing group `Tortola` · `8411:westendsopershole`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8411:westendsopershole` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | British Virgin Islands / `british-virgin-islands` |
| Listing group | Tortola |
| `mrgid` / `zone_name` | 8411 / British Virgin Islands |
| VLIZ EEZ | British Virgin Islands — British Exclusive Economic Zone (British Virgin Islands) (`iso2`=VG, `pol_type`=200NM, sovereign=United Kingdom) |
| seed `country_iso2` | VG |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:36:58Z |
| `geocode_query` | `West End/Sopers Hole` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `West End/Sopers Hole official port of entry OR clearance OR "puerto habilitado" British Virgin Islands` |
| `seed_line` | `West End/Sopers Hole | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `West End/Sopers Hole`, no GPS |

**Reading**

v1 + `probable` seed: `Soper’s Hole Dock / West End Ferry Terminal` (18.3875, -64.7034), plus a `West End` seed. Same Tortola place. Merge, not a new port.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8411** (unchanged 8411)
- Merge target: `8411:sopersholedockwestendferryterminal`
- GPS: **18.3875292, -64.7033916** — Soper’s Hole Dock / West End Ferry Terminal
- Sources:
  - poe_ports v1 Soper’s Hole Dock / West End Ferry Terminal 18.3875292, −64.7033916
  - poe_seed_ports West End probable same coords
- Note: A single Tortola place (Soper’s Hole = West End). Not Bahamas West End. Merge, not a new port.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Soper’s Hole Dock / West End Ferry Terminal | displayed on map | 18.3875292, -64.7033916 |
| `poe_seed_ports` | Soper’s Hole Dock / West End Ferry Terminal | probable | 18.3875292, -64.7033916 |
| `poe_seed_ports` | West End | probable | 18.3875292, -64.7033916 |

**Nearby listing names (treat with caution)**: `West End` (Bahamas).

---

### 6. Grand Mannan Harbour (Grand Manan Island)

**Canada** · listing group `New Brunswick` · `8493:grandmannanharbourgrandmananisland`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8493:grandmannanharbourgrandmananisland` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Canada / `canada` |
| Listing group | New Brunswick |
| `mrgid` / `zone_name` | 8493 / Canada |
| VLIZ EEZ | Canada — Canadian Exclusive Economic Zone (`iso2`=CA, `pol_type`=200NM, sovereign=Canada) |
| seed `country_iso2` | CA |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:37:13Z |
| `geocode_query` | `Grand Mannan Harbour (Grand Manan Island)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Grand Mannan Harbour (Grand Manan Island) official port of entry OR clearance OR "puerto habilitado" Canada` |
| `seed_line` | `Grand Mannan Harbour (Grand Manan Island) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Grand Mannan Harbour (Grand Manan Island)`, no GPS |

**Reading**

Listing spelling “Mannan” instead of Manan. No v1/seed match. Lead: Grand Manan, New Brunswick (Canada).


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8493** (unchanged 8493)
- GPS: **44.7633421, -66.7455097** — North Head Ferry Terminal / North Head Wharf
- Sources:
  - Nominatim OSM North Head Ferry Terminal 44.7633421, −66.7455097 (2026-09-07)
  - CBSA small marine vessel reporting site : North Head Wharf, Grand Manan (Newswire 2020 + CCA cruising guide)
  - Nominatim Grand Harbour (other cove) 44.6704433, −66.7561930 — do not confuse
- Note: Listing typo Mannan → Manan. The documented CBSA PoE is North Head Wharf (also Seal Cove). Grand Harbour is another bay. Canada EEZ 8493 OK.

**Nearby listing names (treat with caution)**: `Grand Harbour` (Malta).

---

### 7. Marigot Bay (St Martin)

**St. Martin** · `8495:marigotbaystmartin`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8495:marigotbaystmartin` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | St. Martin / `st-martin` |
| Listing group | — |
| `mrgid` / `zone_name` | 8495 / Collectivity of Saint Martin |
| VLIZ EEZ | Collectivity of Saint Martin — French Exclusive Economic Zone (Collectivity of Saint Martin) (`iso2`=MF, `pol_type`=200NM, sovereign=France) |
| seed `country_iso2` | MF |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:42:42Z |
| `geocode_query` | `Marigot Bay (St Martin)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Marigot Bay (St Martin) official port of entry OR clearance OR "puerto habilitado" Collectivity of Saint Martin` |
| `seed_line` | `Marigot Bay (St Martin) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Marigot Bay (St Martin)`, no GPS |

**Reading**

Do not confuse with v1 `Marigot Bay Marina` in Saint Lucia (mrgid 8416). Here: Collectivity of Saint Martin (mrgid 8495). The listing also has `Marigot` (another name). Geocode of the compound name missed.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8495** (unchanged 8495)
- Merge target: `8495:marinamarigot`
- GPS: **18.0700053, -63.0884097** — Marina Fort Louis, Marigot
- Sources:
  - Nominatim OSM Marina Fort Louis 18.0700053, −63.0884097 (2026-09-07)
  - Nominatim Marigot town 18.0668544, −63.0848869
  - marinafortlouis.com GPS 18.069901, −63.087788
- Note: FR capital of Saint-Martin, not Marigot Bay Saint Lucia (8416:marigotbaymarina 13.9657, −61.0260). Seed 8495:marinamarigot already probable/accepted without coords: merge + set this GPS on the target. Anse Marcel is another listing PoE.

**Nearby listing names (treat with caution)**: `Marigot` (Dominica), `Marigot Bay` (St. Lucia), `St Martin's` (United Kingdom).

---

### 8. Oyster Pond - St Martin

**St. Martin** · `8495:oysterpondstmartin`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8495:oysterpondstmartin` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | St. Martin / `st-martin` |
| Listing group | — |
| `mrgid` / `zone_name` | 8495 / Collectivity of Saint Martin |
| VLIZ EEZ | Collectivity of Saint Martin — French Exclusive Economic Zone (Collectivity of Saint Martin) (`iso2`=MF, `pol_type`=200NM, sovereign=France) |
| seed `country_iso2` | MF |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:42:41Z |
| `geocode_query` | `Oyster Pond - St Martin` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Oyster Pond - St Martin official port of entry OR clearance OR "puerto habilitado" Collectivity of Saint Martin` |
| `seed_line` | `Oyster Pond - St Martin | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Oyster Pond - St Martin`, no GPS |

**Reading**

The listing also has `Oyster Pond` (no suffix). FR/NL border of the island. No v1 match on 8495.


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu_frontalier` · confidence: **high**
- Correct mrgid: **8495** (unchanged 8495)
- GPS: **18.0549308, -63.0155268** — Oyster Pond (bay, FR/NL border)
- Sources:
  - Nominatim OSM bay Oyster Pond 18.0549308, −63.0155268
  - Nominatim suburb FR 18.0582808, −63.0149083 / village SX 18.0531951, −63.0199401
  - Listing Sint Maarten: Oyster Pond other_port is_port_of_entry=false ; the listing PoE is the FR side
- Note: 1 border pond, 2 admin toponyms. Keep mrgid 8495 (Collectivity of Saint Martin). Not a Marigot duplicate (~8 km). Not Saint Lucia.

**Nearby listing names (treat with caution)**: `Oyster Pond` (Sint Maarten), `St Martin's` (United Kingdom).

---

### 9. Marina Los Morros

**Cuba** · `8406:marinalosmorros`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8406:marinalosmorros` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Cuba / `cuba` |
| Listing group | — |
| `mrgid` / `zone_name` | 8406 / Cuba |
| VLIZ EEZ | Cuba — Cuban Exclusive Economic Zone (`iso2`=CU, `pol_type`=200NM, sovereign=Cuba) |
| seed `country_iso2` | CU |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:38:01Z |
| `geocode_query` | `Marina Los Morros` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Marina Los Morros official port of entry OR clearance OR "puerto habilitado" Cuba` |
| `seed_line` | `Marina Los Morros | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Marina Los Morros`, no GPS |

**Reading**

No v1/OSM/runs occurrence. Name missing from the extracts. Manual Cuba search (Los Morros / marina).


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8406** (unchanged 8406)
- GPS: **21.8999934, -84.9074329** — Marina Cabo San Antonio / Los Morros
- Sources:
  - Nominatim OSM Marina Cabo San Antonio (fuel) 21.8999934, −84.9074329
  - Listing Noonsite position 21°54′07″N, 84°54′30″W = 21.90194, −84.90833
  - Ocean Posse ~21°52′N, 84°56′W (tip, less precise)
- Note: Western tip of Cuba (Guanahacabibes), formerly Club Náutico Cabo San Antonio. Do not take Los Morros / Tazacorte (Canaries) that Nominatim returns on the bare query “Marina Los Morros”.

---

### 10. Cassis

**France** · listing group `Mediterranean Coast (France)` · `5677:cassis`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `5677:cassis` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | France / `france-2` |
| Listing group | Mediterranean Coast (France) |
| `mrgid` / `zone_name` | 5677 / France |
| VLIZ EEZ | France — French Exclusive Economic Zone (`iso2`=FR, `pol_type`=200NM, sovereign=France) |
| seed `country_iso2` | FR |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:38:43Z |
| `geocode_query` | `Cassis` |
| `spatial_kind` | `other_water` — point found but at sea outside the assigned EEZ → rejected |
| `distance_km` | 2.3 |
| `geocode_agree` | True |
| `geocode_arbitration` | spatial_rejected |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Cassis official port of entry OR clearance OR "puerto habilitado" France` |
| `seed_line` | `Cassis | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Cassis`, no GPS |

**Reading**

Like Geelong: Nominatim/GeoNames agree, rejected 2.3 km outside the France EEZ (`other_water`). The harbour is in the calanque, often just outside the polygon. Spatial near-miss.


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **5677** (unchanged 5677)
- GPS: **43.2139518, 5.5360613** — Port de Cassis (marina OSM)
- Sources:
  - Nominatim OSM Port de Cassis marina 43.2139518, 5.5360613 (2026-09-07)
  - geocode_cache Nominatim Cassis admin 43.2140359, 5.5396318 (rejected other_water 2.3 km)
  - GeoNames Cassis 43.21571
- Note: 1 calanque harbour. France EEZ 5677 OK. Spatial near-miss: set the quay (marina) rather than the admin centroid.

---

### 11. Gironde Estuary & Bordeaux

**France** · listing group `Atlantic (France)` · `5677:girondeestuarybordeaux`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `5677:girondeestuarybordeaux` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | France / `france-2` |
| Listing group | Atlantic (France) |
| `mrgid` / `zone_name` | 5677 / France |
| VLIZ EEZ | France — French Exclusive Economic Zone (`iso2`=FR, `pol_type`=200NM, sovereign=France) |
| seed `country_iso2` | FR |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:38:43Z |
| `geocode_query` | `Gironde Estuary & Bordeaux` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Gironde Estuary & Bordeaux official port of entry OR clearance OR "puerto habilitado" France` |
| `seed_line` | `Gironde Estuary & Bordeaux | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Gironde Estuary & Bordeaux`, no GPS |

**Reading**

Region + city, not a quay. `Bordeaux` seed already `probable` (44.8412, -0.5800) and in v1. Merge toward Bordeaux, or point at an office (Pauillac / Le Verdon) if the listing means the estuary.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `region_plus_ville` · confidence: **high**
- Correct mrgid: **5677** (unchanged 5677)
- Merge target: `5677:bordeaux`
- GPS: **44.841225, -0.5800364** — Bordeaux (v1 + probable)
- Variant: 45.547543, -1.0622993 — Le Verdon-sur-Mer (mouth, if a coastal point is wanted)
- Sources:
  - poe_ports v1 Bordeaux 44.841225, −0.5800364
  - Nominatim Bordeaux identical
- Note: The estuary is not a quay. The listing names Bordeaux. Merge. Le Verdon / Pauillac = possible offices downstream, not a second listing PoE.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| `poe_seed_ports` | Bordeaux | probable | 44.841225, -0.5800364 |

---

### 12. Gulfe de Fos (Port St Louis, Port Napoleon, St-Gervais)

**France** · listing group `Mediterranean Coast (France)` · `5677:gulfedefosportstlouisportnapoleonstgerva`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `5677:gulfedefosportstlouisportnapoleonstgerva` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | France / `france-2` |
| Listing group | Mediterranean Coast (France) |
| `mrgid` / `zone_name` | 5677 / France |
| VLIZ EEZ | France — French Exclusive Economic Zone (`iso2`=FR, `pol_type`=200NM, sovereign=France) |
| seed `country_iso2` | FR |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:38:44Z |
| `geocode_query` | `Gulfe de Fos (Port St Louis, Port Napoleon, St-Gervais)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Gulfe de Fos (Port St Louis, Port Napoleon, St-Gervais) official port of entry OR clearance OR "puerto habilitado" France` |
| `seed_line` | `Gulfe de Fos (Port St Louis, Port Napoleon, St-Gervais) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Gulfe de Fos (Port St Louis, Port Napoleon, St-Gervais)`, no GPS |

**Reading**

Broken name (“Gulfe”) + three toponyms of the Golfe de Fos. Port Napoléon is the marina of Port-Saint-Louis-du-Rhône; Saint-Gervais is the yacht harbour of Fos-sur-Mer. Two yacht places, not three.

**Verification** (2026-09-07)

- Decision: `scinder` · kind: `3_noms_2_ports_plaisance` · confidence: **high**
- Correct mrgid: **5677** (unchanged 5677)
- GPS Port Napoléon (Port-Saint-Louis-du-Rhône): **43.3758376, 4.8316198** (Nominatim OSM marina Port Napoléon)
- GPS Port Saint-Gervais / Claude Rossi (Fos-sur-Mer): **43.4277969, 4.9420273** (Nominatim OSM marina Port Saint-Gervais ; fossurmer.fr)
- Sources:
  - Nominatim Port Napoléon 43.3758376, 4.8316198
  - Nominatim Port Saint-Gervais 43.4277969, 4.9420273
  - Navily / MarinaSpots Port Napoleon 43°22.56′N, 4°49.86′E
  - Fos-sur-Mer town hall: port Claude Rossi pointe Saint-Gervais (formerly Saint-Gervais)
- Note: Typo Gulfe → Golfe. Port Napoléon is INSIDE Port-Saint-Louis-du-Rhône (1 commune, 1 pleasure marina). Saint-Gervais = Fos-sur-Mer, ~8 km. Split into 2 yacht points. No v1 twin. Sibling listing “Fos” = this record, not a 4th port.

---

### 13. Christmas Island/Kiritimati

**Kiribati** · listing group `Line Islands` · `8488:christmasislandkiritimati`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8488:christmasislandkiritimati` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Kiribati / `kiribati` |
| Listing group | Line Islands |
| `mrgid` / `zone_name` | 8488 / Gilbert Islands |
| VLIZ EEZ | Gilbert Islands — Kiribati Exclusive Economic Zone (Gilbert Islands) (`iso2`=KI, `pol_type`=200NM, sovereign=Kiribati) |
| seed `country_iso2` | KI |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:40:36Z |
| `geocode_query` | `Christmas Island/Kiritimati` |
| `spatial_kind` | `other_water` — point found but at sea outside the assigned EEZ → rejected |
| `distance_km` | 2529.9 |
| `geocode_agree` | None |
| `geocode_arbitration` | spatial_rejected |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Christmas Island/Kiritimati official port of entry OR clearance OR "puerto habilitado" Gilbert Islands` |
| `seed_line` | `Christmas Island/Kiritimati | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Christmas Island/Kiritimati`, no GPS |

**Reading**

Double trap: (1) “Christmas Island” often means the Australian island, not Kiritimati; (2) the record is filed under the Gilbert Islands EEZ (8488) while Kiritimati is in Line Group (mrgid 8441). `other_water` rejection at 2529 km. A `Christmas Island Port` unverified seed exists without coords. Correct the EEZ to 8441 then geocode “Kiritimati” / London, Christmas Island.


**Verification** (2026-09-07)

- Decision: `corriger_zee` · kind: `1_lieu_mauvaise_zee` · confidence: **high**
- Correct mrgid: **8441** (Line Group)
- New key: `8441:christmasislandkiritimati`
- GPS: **2.0075, -157.48583333** — Port of Navy Harbour, London / Ronton, Kiritimati
- Variant: 2.003017, -157.4820927 — London village OSM
- Sources:
  - LogCluster / KPA Port of Navy Harbour 2.0075°N, 157.48583333°W
  - Nominatim London, Kiritimati 2.003017, −157.4820927 (Line Islands, KI)
  - Wikipedia London, Kiribati 1.98333°N, 157.47500°W
  - eez_index mrgid 8441 Line Group ; listing group = Line Islands
- Note: NOT Christmas Island AU (8309:portofchristmasisland, DAFF −10.4, 105.66). NOT Phoenix 8450 (8450:kiritimatiseaport probable/accepted WITHOUT coords = wrong EEZ). The Line Group twin is 8441:kiritimatiseaport (unverified/inconclusive, no GPS): merge and set Navy Harbour there. slug_overrides kiribati=[8488,8450,8441] took the first.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| `poe_seed_ports` | Christmas Island Port | unverified / rejected | None, None |

---

### 14. Tyrell Bay & Hillsborough (Carriacou)

**Grenada** · `8419:tyrellbayhillsboroughcarriacou`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8419:tyrellbayhillsboroughcarriacou` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Grenada / `grenada` |
| Listing group | — |
| `mrgid` / `zone_name` | 8419 / Grenada |
| VLIZ EEZ | Grenada — Grenadian Exclusive Economic Zone (`iso2`=GD, `pol_type`=200NM, sovereign=Grenada) |
| seed `country_iso2` | GD |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:39:21Z |
| `geocode_query` | `Tyrell Bay & Hillsborough (Carriacou)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Tyrell Bay & Hillsborough (Carriacou) official port of entry OR clearance OR "puerto habilitado" Grenada` |
| `seed_line` | `Tyrell Bay & Hillsborough (Carriacou) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Tyrell Bay & Hillsborough (Carriacou)`, no GPS |

**Reading**

Two Carriacou bays. v1 has `Port of Hillsborough` (12.4833, -61.4568). Tyrell Bay is another anchorage. Merge Hillsborough + Tyrell point, or split.


**Verification** (2026-09-07)

- Decision: `scinder` · kind: `2_lieux` · confidence: **high**
- Correct mrgid: **8419** (unchanged 8419)
- GPS Port of Hillsborough (`8419:portofhillsborough`): **12.4833286, -61.4567557** (v1 poe_ports)
- GPS Tyrrel / Tyrell Bay Marina: **12.4621, -61.4860667** (tyrellbaymarinacarriacou.com 12°27.726′N, 61°29.164′W)
- Sources:
  - poe_ports v1 Port of Hillsborough 12.4833286, −61.4567557
  - Tyrell Bay Marina official site 12°27.726′N 61°29.164′W
  - Nominatim OSM Tyrrel Bay 12.4580658, −61.4870166
- Note: Two Carriacou bays (~4 km). Hillsborough = v1 PoE. Tyrell/Tyrrel Bay = marina/boatyard (Harvey Vale). Split: merge Hillsborough + nouveau_point Tyrell.

**Already in the database (same EEZ, other `dedup_key`)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Port of Hillsborough | displayed on map | 12.4833286, -61.4567557 |

---

### 15. Barbers Point Harbour (Ko Olina)

**Hawaii** · listing group `Oahu` · `8453:barberspointharbourkoolina`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8453:barberspointharbourkoolina` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Hawaii / `hawaii` |
| Listing group | Oahu |
| `mrgid` / `zone_name` | 8453 / Hawaii |
| VLIZ EEZ | Hawaii — United States Exclusive Economic Zone (Hawaii) (`iso2`=None, `pol_type`=200NM, sovereign=United States) |
| seed `country_iso2` | *(null)* |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:39:33Z |
| `geocode_query` | `Barbers Point Harbour (Ko Olina)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Barbers Point Harbour (Ko Olina) official port of entry OR clearance OR "puerto habilitado" Hawaii` |
| `seed_line` | `Barbers Point Harbour (Ko Olina) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Barbers Point Harbour (Ko Olina)`, no GPS |

**Reading**

Hawaii (8453), VLIZ-side iso2 null (normal). Ko Olina / Barbers Point, Oahu. No v1 match. Honolulu is the sibling listing of the Oahu group.


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_complexe_adjacent` · confidence: **high**
- Correct mrgid: **8453** (unchanged 8453)
- GPS: **21.3278642, -158.1196613** — KoʻOlina Marina (yacht)
- Variant: 21.325, -158.1177778 — Kalaeloa Barbers Point Harbor (commercial USNAX)
- Sources:
  - Nominatim OSM Ko'Olina Marina 21.3278642, −158.1196613
  - kalaeloaharbor.com 21°19′30″N, 158°07′04″W
  - MarineRadar USNAX ~21.3147, −158.0942
- Note: Hawaii EEZ 8453 already correct (VLIZ iso2 null = normal). Ko Olina and Barbers Point are adjacent (~400 m–2 km). 1 west Oahu complex, distinct from Honolulu v1 (21.3045, −157.8557). CBP lists Honolulu as the Hawaii PoE; Barbers Point = commercial port. The listing treats them separately: yacht nouveau_point at Ko Olina.

---

### 16. Andaman Islands

**India** · `8480:andamanislands`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8480:andamanislands` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | India / `india` |
| Listing group | — |
| `mrgid` / `zone_name` | 8480 / India |
| VLIZ EEZ | India — Indian Exclusive Economic Zone (`iso2`=IN, `pol_type`=200NM, sovereign=India) |
| seed `country_iso2` | IN |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:39:36Z |
| `geocode_query` | `Andaman Islands` |
| `spatial_kind` | `inland` — point found but too far inland / outside the river exception → rejected |
| `distance_km` | 697.8 |
| `geocode_agree` | False |
| `geocode_arbitration` | spatial_rejected |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Andaman Islands official port of entry OR clearance OR "puerto habilitado" India` |
| `seed_line` | `Andaman Islands | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Andaman Islands`, no GPS |

**Reading**

This is not a port, it is an archipelago. Assigned to the mainland India EEZ (8480), while Port Blair v1 is in the Andaman and Nicobar EEZ (8333) (11.6730, 92.7460). Inland rejection 698 km (wrong polygon / toponym too broad). Action: merge with Port Blair or recreate on mrgid 8333.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `region` · confidence: **high**
- Correct mrgid: **8333** (Andaman and Nicobar)
- Merge target: `8333:portofportblair`
- GPS: **11.6730477, 92.7460414** — Port of Port Blair
- Sources:
  - poe_ports v1 Port of Port Blair 11.6730477, 92.7460414 mrgid 8333
  - Nominatim Port Blair 11.6645348, 92.7390448
  - eez_index 8333 Andaman and Nicobar
- Note: Archipelago, not a quay. Inland 698 km = wrong polygon 8480 (mainland India). Do not recreate on 8480. Merge toward Port Blair 8333. Car Nicobar (8333) is another place.

**Already in the database (other EEZ)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Port of Port Blair (mrgid **8333**) | displayed on map | 11.6730477, 92.7460414 |

---

### 17. Bandar Bintan Telani (BBT) – Bintan Island

**Indonesia** · listing group `Western Indonesia - Bintan, Lingga, Riau and Anambas Islands` · `8492:bandarbintantelanibbtbintanisland`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8492:bandarbintantelanibbtbintanisland` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Indonesia / `indonesia` |
| Listing group | Western Indonesia - Bintan, Lingga, Riau and Anambas Islands |
| `mrgid` / `zone_name` | 8492 / Indonesia |
| VLIZ EEZ | Indonesia — Indonesian Exclusive Economic Zone (`iso2`=ID, `pol_type`=200NM, sovereign=Indonesia) |
| seed `country_iso2` | ID |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:40:00Z |
| `geocode_query` | `Bandar Bintan Telani (BBT) – Bintan Island` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Bandar Bintan Telani (BBT) – Bintan Island official port of entry OR clearance OR "puerto habilitado" Indonesia` |
| `seed_line` | `Bandar Bintan Telani (BBT) – Bintan Island | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Bandar Bintan Telani (BBT) – Bintan Island`, no GPS |

**Reading**

`Bandar Bintan Telani` seed already `probable` (1.1605, 104.3202). `Tanjung Pinang (Bintan Island)` is `confirmed` but with lat **-3.36** (Bintan is ~1.2°N: suspect point). Merge with Bandar Bintan Telani.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8492** (unchanged 8492)
- Merge target: `8492:bandarbintantelani`
- GPS: **1.1605006, 104.3201677** — Bandar Bentan Telani ferry terminal
- Sources:
  - poe_seed_ports Bandar Bintan Telani probable 1.1605006, 104.3201677
  - Nominatim Bandar Bentan Telani identical
- Note: Same terminal. Tanjung Pinang confirmed (−3.3564491, 104.6571166) is another port AND a suspect GPS (Bintan ≈ 1.16°N ; −3.36° / 104.66° ≈ southern Sumatra / Palembang). Do not merge toward Tanjung Pinang.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| `poe_seed_ports` | Bandar Bintan Telani | probable | 1.1605006, 104.3201677 |
| `poe_seed_ports` | Tanjung Pinang (Bintan Island, Riau Islands) | confirmed / accepted | -3.3564491, 104.6571166 |

**Nearby listing names (treat with caution)**: `Tanjung Pinang (Bintan Island, Riau Islands)` (Indonesia).

---

### 18. Bowden Harbour/Port Morant

**Jamaica** · `8459:bowdenharbourportmorant`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8459:bowdenharbourportmorant` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Jamaica / `jamaica` |
| Listing group | — |
| `mrgid` / `zone_name` | 8459 / Jamaica |
| VLIZ EEZ | Jamaica — Jamaican Exclusive Economic Zone (`iso2`=JM, `pol_type`=200NM, sovereign=Jamaica) |
| seed `country_iso2` | JM |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:40:14Z |
| `geocode_query` | `Bowden Harbour/Port Morant` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Bowden Harbour/Port Morant official port of entry OR clearance OR "puerto habilitado" Jamaica` |
| `seed_line` | `Bowden Harbour/Port Morant | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Bowden Harbour/Port Morant`, no GPS |

**Reading**

Jamaica compound name. No v1. Port Morant / Bowden, east coast. Split or one point.


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8459** (unchanged 8459)
- GPS: **17.88718, -76.31667** — Bowden Wharf / Coast Guard, Port Morant
- Sources:
  - Cruiserswiki Port Morant Bowden Wharf 17.88718, −76.31667
  - Nominatim Bowden hamlet 17.8895747, −76.3130602 (inside Port Morant)
  - Listing Noonsite 17°53.11′N, 76°19.06′W = 17.88517, −76.31767
- Note: A single harbour (SE Jamaica coast). Bowden is the hamlet / wharf inside Port Morant. Not two PoEs. EEZ 8459 OK.

---

### 19. Khuludhufushi

**Maldives** · listing group `Upper North Province` · `8345:khuludhufushi`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8345:khuludhufushi` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Maldives / `maldives` |
| Listing group | Upper North Province |
| `mrgid` / `zone_name` | 8345 / Maldives |
| VLIZ EEZ | Maldives — Maldivian Exclusive Economic Zone (`iso2`=MV, `pol_type`=200NM, sovereign=Maldives) |
| seed `country_iso2` | MV |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:40:56Z |
| `geocode_query` | `Khuludhufushi` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Khuludhufushi official port of entry OR clearance OR "puerto habilitado" Maldives` |
| `seed_line` | `Khuludhufushi | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Khuludhufushi`, no GPS |

**Reading**

Very likely a typo for Khulhudhuffushi (Haa Dhaalu, Maldives). No match. Fix the spelling before geocode.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu_faute` · confidence: **high**
- Correct mrgid: **8345** (unchanged 8345)
- Merge target: `8345:kulhudhuffushiport`
- GPS: **6.6233167, 73.0694663** — Kulhudhuffushi Port
- Sources:
  - poe_ports v1 Kulhudhuffushi Port 6.6233167, 73.0694663
  - Nominatim Kulhudhuffushi 6.6233167, 73.0694663
- Note: Listing typo Khuludhufushi → Kulhudhuffushi (Haa Dhaalu). The v1+probable twin already exists. Merge, not a new point.

---

### 20. Puerto Vallarta/ Banderas Bay

**Mexico** · listing group `West Coast (Mexico)` · `8429:puertovallartabanderasbay`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8429:puertovallartabanderasbay` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Mexico / `mexico` |
| Listing group | West Coast (Mexico) |
| `mrgid` / `zone_name` | 8429 / Mexico |
| VLIZ EEZ | Mexico — Mexican Exclusive Economic Zone (`iso2`=MX, `pol_type`=200NM, sovereign=Mexico) |
| seed `country_iso2` | MX |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:41:18Z |
| `geocode_query` | `Puerto Vallarta/ Banderas Bay` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Puerto Vallarta/ Banderas Bay official port of entry OR clearance OR "puerto habilitado" Mexico` |
| `seed_line` | `Puerto Vallarta/ Banderas Bay | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Puerto Vallarta/ Banderas Bay`, no GPS |

**Reading**

v1 + `probable` seed `Puerto Vallarta` (20.6561, -105.2435). Banderas Bay is the bay, not a second PoE. Merge.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu_plus_baie` · confidence: **high**
- Correct mrgid: **8429** (unchanged 8429)
- Merge target: `8429:puertovallarta`
- GPS: **20.6561446, -105.243527** — Puerto Vallarta
- Sources:
  - poe_ports v1 Puerto Vallarta 20.6561446, −105.243527
  - Nuevo Vallarta v1 20.6913097, −105.291834 is another marina (do not merge)
- Note: Banderas Bay = the bay, not a 2nd PoE. Merge toward Puerto Vallarta. Nuevo Vallarta stays separate.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Puerto Vallarta | displayed on map | 20.6561446, -105.243527 |
| `poe_seed_ports` | Puerto Vallarta | probable | 20.6561446, -105.243527 |

---

### 21. Colonia, Yap Island

**Federated States of Micronesia** · listing group `Yap State` · `8316:coloniayapisland`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8316:coloniayapisland` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Federated States of Micronesia / `federated-states-of-micronesia` |
| Listing group | Yap State |
| `mrgid` / `zone_name` | 8316 / Micronesia |
| VLIZ EEZ | Micronesia — Micronesian Exclusive Economic Zone (`iso2`=FM, `pol_type`=200NM, sovereign=Micronesia) |
| seed `country_iso2` | FM |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:38:40Z |
| `geocode_query` | `Colonia, Yap Island` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Colonia, Yap Island official port of entry OR clearance OR "puerto habilitado" Micronesia` |
| `seed_line` | `Colonia, Yap Island | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Colonia, Yap Island`, no GPS |

**Reading**

Colonia (Yap). No v1. Do not merge with Colonia del Sacramento (Uruguay) present in v1.


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8316** (unchanged 8316)
- GPS: **9.5162421, 138.121629** — Colonia (Yap)
- Sources:
  - Nominatim OSM Colonia, Yap 9.5162421, 138.121629
  - UN/LOCODE FMYAP / MagicPort 9.52, 138.13
- Note: Capital of Yap / Tomil Harbour. DO NOT merge with Colonia del Sacramento (Uruguay v1 −34.47, −57.84) nor Yap International Airport (9.4979, 138.0864).

---

### 22. Lele/Leluh Harbour

**Federated States of Micronesia** · listing group `Kosrae` · `8316:leleleluhharbour`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8316:leleleluhharbour` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Federated States of Micronesia / `federated-states-of-micronesia` |
| Listing group | Kosrae |
| `mrgid` / `zone_name` | 8316 / Micronesia |
| VLIZ EEZ | Micronesia — Micronesian Exclusive Economic Zone (`iso2`=FM, `pol_type`=200NM, sovereign=Micronesia) |
| seed `country_iso2` | FM |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:38:38Z |
| `geocode_query` | `Lele/Leluh Harbour` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Lele/Leluh Harbour official port of entry OR clearance OR "puerto habilitado" Micronesia` |
| `seed_line` | `Lele/Leluh Harbour | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Lele/Leluh Harbour`, no GPS |

**Reading**

Lele / Lelu / Leluh = a single harbour on Kosrae. A `Lelu Harbor` seed already exists as `probable`. Okat Harbour (same listing group) is the island’s other PoE.

**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8316** (unchanged 8316)
- Merge target: `8316:leluharbor`
- GPS: **5.3324023, 163.0241705** — Lelu Harbor, Kosrae
- Sources:
  - poe_seed_ports Lelu Harbor probable 5.3324023, 163.0241705
  - Nominatim Lelu, Kosrae identical
- Note: Lele / Lelu / Leluh = same Kosrae harbour. Okat Harbour (8316:okatharbor confirmed 5.3233, 162.97) is the other listing PoE of the Kosrae group — do not merge.

---

### 23. Tanapag Harbour (Saipan)

**Northern Marianas** · `48980:tanapagharboursaipan`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `48980:tanapagharboursaipan` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Northern Marianas / `northern-marianas` |
| Listing group | — |
| `mrgid` / `zone_name` | 48980 / Northern Mariana Islands |
| VLIZ EEZ | Northern Mariana Islands — United States Exclusive Economic Zone (Northern Mariana Islands) (`iso2`=MP, `pol_type`=200NM, sovereign=United States) |
| seed `country_iso2` | MP |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:41:49Z |
| `geocode_query` | `Tanapag Harbour (Saipan)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Tanapag Harbour (Saipan) official port of entry OR clearance OR "puerto habilitado" Northern Mariana Islands` |
| `seed_line` | `Tanapag Harbour (Saipan) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Tanapag Harbour (Saipan)`, no GPS |

**Reading**

`Saipan` seed already `probable` (15.1685). Tanapag is Saipan’s commercial port. Merge or a more precise point on the Tanapag quay.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **48980** (unchanged 48980)
- Merge target: `48980:saipan`
- GPS: **15.22667, 145.73667** — Tanapag Harbor (more precise than the Saipan centroid)
- Sources:
  - Wikipedia Tanapag Harbor 15°13′36″N 145°44′12″E = 15.22667, 145.73667
  - poe_seed_ports Saipan probable/accepted 15.16847, 145.74081 (island / Garapan)
  - Nominatim Tanapag locality 15.2418863, 145.7572312
- Note: Tanapag = Saipan commercial port (the country’s only listing PoE). Merge toward 48980:saipan. Option: $set the Saipan GPS to 15.22667, 145.73667 (quay rather than centroid).

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| `poe_seed_ports` | Saipan | probable / accepted | 15.16847, 145.74081 |

---

### 24. Longyearbyen

**Norway** · listing group `Svalbard (Spitsbergen)` · `5686:longyearbyen`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `5686:longyearbyen` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Norway / `norway` |
| Listing group | Svalbard (Spitsbergen) |
| `mrgid` / `zone_name` | 5686 / Norway |
| VLIZ EEZ | Norway — Norwegian Exclusive Economic Zone (`iso2`=NO, `pol_type`=200NM, sovereign=Norway) |
| seed `country_iso2` | NO |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:41:47Z |
| `geocode_query` | `Longyearbyen` |
| `spatial_kind` | `inland` — point found but too far inland / outside the river exception → rejected |
| `distance_km` | 520.2 |
| `geocode_agree` | True |
| `geocode_arbitration` | spatial_rejected |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Longyearbyen official port of entry OR clearance OR "puerto habilitado" Norway` |
| `seed_line` | `Longyearbyen | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Longyearbyen`, no GPS |

**Reading**

Geocoders agree, but rejected `inland` 520 km from the mainland Norway EEZ (5686). Longyearbyen is on Svalbard: the continental 200NM polygon does not cover it. Listing group = Svalbard (Spitsbergen). A Svalbard EEZ is missing from the assignment.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu_mauvaise_zee` · confidence: **high**
- Correct mrgid: **33181** (Svalbard)
- Merge target: `33181:longyearbyen`
- GPS: **78.22334, 15.64689** — Longyearbyen (already in the database on 33181)
- Sources:
  - poe_seed_ports 33181:longyearbyen probable 78.22334, 15.64689
  - Nominatim Longyearbyen 78.2231558, 15.6463656 (Svalbard, Norge)
  - eez_index mrgid 33181 Svalbard iso2=SJ
- Note: The point already exists on the correct EEZ. The 5686 name_only is the mainland duplicate (inland 520 km). Merge / abandon 5686:longyearbyen. Do not recreate. Svalbard was missing from slug_overrides norway.

---

### 25. San Carlos - Vista Mar Marina

**Panama** · listing group `Pacific (Panama)` · `8423:sancarlosvistamarmarina`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8423:sancarlosvistamarmarina` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Panama / `panama` |
| Listing group | Pacific (Panama) |
| `mrgid` / `zone_name` | 8423 / Panama |
| VLIZ EEZ | Panama — Panamanian Exclusive Economic Zone (`iso2`=PA, `pol_type`=200NM, sovereign=Panama) |
| seed `country_iso2` | PA |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:42:00Z |
| `geocode_query` | `San Carlos - Vista Mar Marina` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `San Carlos - Vista Mar Marina official port of entry OR clearance OR "puerto habilitado" Panama` |
| `seed_line` | `San Carlos - Vista Mar Marina | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `San Carlos - Vista Mar Marina`, no GPS |

**Reading**

Do not take the Mexican v1 San Carlos (Baja / Sonora). Here: Pacific Panama. Vista Mar Marina, San Carlos (western Panama).


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8423** (unchanged 8423)
- GPS: **8.4823008, -79.9435075** — Vista Mar Marina, San Carlos, Panamá Oeste
- Sources:
  - Nominatim OSM Vista Mar Marina 8.4823008, −79.9435075
  - Listing Noonsite 08°29.10′N, 79°56.40′W = 8.485, −79.94 (map 8.48611, −79.94444)
- Note: Pacific Panama, not San Carlos Baja (24.79, −112.12) nor Sonora (27.95, −111.06). Immigration on site; cruising permit in Panama City per the listing. EEZ 8423 OK.

**Nearby listing names (treat with caution)**: `San Carlos` (Mexico).

---

### 26. Prince Edward Island

**Marion & Prince Edward Island** · `8384:princeedwardisland`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8384:princeedwardisland` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Marion & Prince Edward Island / `marion-prince-edward-island` |
| Listing group | — |
| `mrgid` / `zone_name` | 8384 / Prince Edward Islands |
| VLIZ EEZ | Prince Edward Islands — South African Exclusive Economic Zone (Prince Edward Islands) (`iso2`=None, `pol_type`=200NM, sovereign=South Africa) |
| seed `country_iso2` | *(null)* |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:40:55Z |
| `geocode_query` | `Prince Edward Island` |
| `spatial_kind` | `inland` — point found but too far inland / outside the river exception → rejected |
| `distance_km` | 13906.6 |
| `geocode_agree` | False |
| `geocode_arbitration` | spatial_rejected |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Prince Edward Island official port of entry OR clearance OR "puerto habilitado" Prince Edward Islands` |
| `seed_line` | `Prince Edward Island | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Prince Edward Island`, no GPS |

**Reading**

Violent homonym: the “Marion & Prince Edward Island” listing is South African subantarctic (mrgid 8384). The geocoder aimed at Canadian Prince Edward Island → inland 13,907 km. There is probably no pleasure-craft PoE there; Marion / Prince Edward are bases. Check whether the listing is relevant.


**Verification** (2026-09-07)

- Decision: `abandonner` · kind: `region_pas_poe` · confidence: **high**
- Correct mrgid: **8384** (unchanged 8384)
- GPS: none (do not set the homonym)
- Island (ref. only): -46.6365552, 37.946448 — Prince Edward Island (ZA subantarctic) — island, not a port
- Sources:
  - Nominatim Prince Edward Island ZA −46.6365552, 37.946448
  - Marion Island OSM −46.9029708, 37.7527452
  - SANAP / Prince Edward Islands Management Plan: Special Nature Reserve, no tourism ashore
  - MPA regulation: Sanctuary 12 NM, vessel entry forbidden except State / force majeure
- Note: Listing “Marion & Prince Edward Island” = ZA archipelago, EEZ 8384 correct. The geocoder aimed at Canada (inland 13,907 km). No pleasure-craft PoE. Do not set the Canadian GPS. Abandon the record.

---

### 27. Britannia Bay, Lovell

**St. Vincent & the Grenadines** · listing group `Mustique` · `8421:britanniabaylovell`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8421:britanniabaylovell` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | St. Vincent & the Grenadines / `st-vincent-the-grenadines` |
| Listing group | Mustique |
| `mrgid` / `zone_name` | 8421 / Saint Vincent and the Grenadines |
| VLIZ EEZ | Saint Vincent and the Grenadines — Saint Vincentian Exclusive Economic Zone (`iso2`=VC, `pol_type`=200NM, sovereign=Saint Vincent and the Grenadines) |
| seed `country_iso2` | VC |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:42:46Z |
| `geocode_query` | `Britannia Bay, Lovell` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Britannia Bay, Lovell official port of entry OR clearance OR "puerto habilitado" Saint Vincent and the Grenadines` |
| `seed_line` | `Britannia Bay, Lovell | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Britannia Bay, Lovell`, no GPS |

**Reading**

Mustique (listing group). v1 has `Mustique` (12.8760, -61.1828). Britannia Bay / Lovell Village = Mustique’s main anchorage. Probable merge.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8421** (unchanged 8421)
- Merge target: `8421:mustique`
- GPS: **12.8760094, -61.1828409** — Mustique (v1) — Britannia Bay anchorage
- Variant: 12.8792913, -61.1889553 — Britannia Bay (OSM bay, more precise)
- Sources:
  - poe_ports v1 Mustique 12.8760094, −61.1828409
  - Nominatim Britannia Bay 12.8792913, −61.1889553
- Note: Listing group Mustique. Britannia Bay / Lovell Village = the main anchorage. Not Britannia Bay South Africa nor Ontario. Merge toward Mustique; option to refine toward the bay.

**Already in the database (same EEZ)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Mustique | displayed on map | 12.8760094, -61.1828409 |

---

### 28. Lata, Ndendo Island (Santa Cruz Islands)

**Solomon Islands** · listing group `Outer Islands/Atolls (Solomon islands)` · `8314:latandendoislandsantacruzislands`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8314:latandendoislandsantacruzislands` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Solomon Islands / `solomon-islands` |
| Listing group | Outer Islands/Atolls (Solomon islands) |
| `mrgid` / `zone_name` | 8314 / Solomon Islands |
| VLIZ EEZ | Solomon Islands — Solomon Islands Exclusive Economic Zone (`iso2`=SB, `pol_type`=200NM, sovereign=Solomon Islands) |
| seed `country_iso2` | SB |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:42:24Z |
| `geocode_query` | `Lata, Ndendo Island (Santa Cruz Islands)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Lata, Ndendo Island (Santa Cruz Islands) official port of entry OR clearance OR "puerto habilitado" Solomon Islands` |
| `seed_line` | `Lata, Ndendo Island (Santa Cruz Islands) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Lata, Ndendo Island (Santa Cruz Islands)`, no GPS |

**Reading**

v1 + `probable` seed `Lata` (-10.7244, 165.7982). Same Ndendo island. Merge.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **8314** (unchanged 8314)
- Merge target: `8314:lata`
- GPS: **-10.7244151, 165.7982204** — Lata (Ndendo / Temotu)
- Sources:
  - poe_seed_ports Lata probable −10.7244151, 165.7982204
  - poe_ports v1 Lata same coords
  - Nominatim Lata, Solomon Islands −10.7241726, 165.7977641
- Note: Same town. Do not match the Santa Cruz of the Canaries / Azores. Merge.

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| `poe_seed_ports` | Lata | probable | -10.7244151, 165.7982204 |

**Nearby listing names (treat with caution)**: `Tanjung Pinang (Bintan Island, Riau Islands)` (Indonesia).

---

### 29. Ria de Vigo and Baiona

**Spain** · listing group `North West Spain` · `5693:riadevigoandbaiona`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `5693:riadevigoandbaiona` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | Spain / `spain` |
| Listing group | North West Spain |
| `mrgid` / `zone_name` | 5693 / Spain |
| VLIZ EEZ | Spain — Spanish Exclusive Economic Zone (`iso2`=ES, `pol_type`=200NM, sovereign=Spain) |
| seed `country_iso2` | ES |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:42:31Z |
| `geocode_query` | `Ria de Vigo and Baiona` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Ria de Vigo and Baiona official port of entry OR clearance OR "puerto habilitado" Spain` |
| `seed_line` | `Ria de Vigo and Baiona | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Ria de Vigo and Baiona`, no GPS |

**Reading**

Ría (body of water) + Baiona. Two possible ports: Vigo and Baiona. Compound name → miss. Split.


**Verification** (2026-09-07)

- Decision: `scinder` · kind: `2_lieux` · confidence: **high**
- Correct mrgid: **5693** (unchanged 5693)
- GPS Porto de Vigo: **42.2413406, -8.7265604** (Nominatim OSM marina Porto de Vigo)
- GPS Porto Deportivo de Baiona: **42.1184779, -8.8451206** (Nominatim OSM Puerto Deportivo de Baiona)
- Sources:
  - Nominatim Porto de Vigo 42.2413406, −8.7265604 (Galicia, not the Vigo/Asturias hamlet)
  - Nominatim Porto Deportivo de Baiona 42.1184779, −8.8451206
- Note: Ría = body of water. Two ports ~16 km. No v1 twin. Split into 2 nouveau_point. Query “Puerto de Vigo” without Galicia lands on Asturias.

---

### 30. Cowes & R. Medina (Isle of Wight)

**United Kingdom** · listing group `South Coast` · `5696:cowesrmedinaisleofwight`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `5696:cowesrmedinaisleofwight` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | United Kingdom / `united-kingdom` |
| Listing group | South Coast |
| `mrgid` / `zone_name` | 5696 / United Kingdom |
| VLIZ EEZ | United Kingdom — British Exclusive Economic Zone (`iso2`=GB, `pol_type`=200NM, sovereign=United Kingdom) |
| seed `country_iso2` | GB |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:43:37Z |
| `geocode_query` | `Cowes & R. Medina (Isle of Wight)` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Cowes & R. Medina (Isle of Wight) official port of entry OR clearance OR "puerto habilitado" United Kingdom` |
| `seed_line` | `Cowes & R. Medina (Isle of Wight) | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Cowes & R. Medina (Isle of Wight)`, no GPS |

**Reading**

Cowes + Medina. Compound name → miss. No v1 Cowes. South Coast listing siblings: Dover, Falmouth, Plymouth, Portsmouth, Southampton Water.


**Verification** (2026-09-07)

- Decision: `nouveau_point` · kind: `1_lieu` · confidence: **high**
- Correct mrgid: **5696** (unchanged 5696)
- GPS: **50.7614678, -1.2966036** — Cowes Yacht Haven
- Sources:
  - Nominatim OSM Cowes Yacht Haven marina 50.7614678, −1.2966036
  - Nominatim Cowes town 50.7633176, −1.2985186
  - cowes.co.uk Cowes Harbour
- Note: Cowes + Medina = one estuary, one PoE. The river leads to Newport but yacht clearance is Cowes. No v1. Single nouveau_point.

---

### 31. Oban/Dunstaffnage

**United Kingdom** · listing group `Scotland` · `5696:obandunstaffnage`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `5696:obandunstaffnage` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | United Kingdom / `united-kingdom` |
| Listing group | Scotland |
| `mrgid` / `zone_name` | 5696 / United Kingdom |
| VLIZ EEZ | United Kingdom — British Exclusive Economic Zone (`iso2`=GB, `pol_type`=200NM, sovereign=United Kingdom) |
| seed `country_iso2` | GB |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:43:36Z |
| `geocode_query` | `Oban/Dunstaffnage` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Oban/Dunstaffnage official port of entry OR clearance OR "puerto habilitado" United Kingdom` |
| `seed_line` | `Oban/Dunstaffnage | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Oban/Dunstaffnage`, no GPS |

**Reading**

Two Scotland sites (Oban and Dunstaffnage marina). Compound name → miss. Split or Oban.


**Verification** (2026-09-07)

- Decision: `scinder` · kind: `2_lieux` · confidence: **high**
- Correct mrgid: **5696** (unchanged 5696)
- GPS Oban North Pier: **56.4148317, -5.474593** (Nominatim OSM North Pier Oban)
- GPS Dunstaffnage Marina: **56.4498834, -5.4325487** (Nominatim OSM Dunstaffnage Marina)
- Sources:
  - Nominatim North Pier Oban 56.4148317, −5.4745930
  - Nominatim Dunstaffnage Marina 56.4498834, −5.4325487
- Note: Two sites ~4.5 km. Oban = town / pier; Dunstaffnage = marina (Dunbeg). Split. Nominatim “Oban Harbour” returned a manicure salon — ignore.

---

### 32. Ketchikan

**USA** · listing group `USA - Alaska` · `8456:ketchikan`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8456:ketchikan` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | USA / `usa` |
| Listing group | USA - Alaska |
| `mrgid` / `zone_name` | 8456 / United States |
| VLIZ EEZ | United States — United States Exclusive Economic Zone (`iso2`=US, `pol_type`=200NM, sovereign=United States) |
| seed `country_iso2` | US |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:44:19Z |
| `geocode_query` | `Ketchikan` |
| `spatial_kind` | `inland` — point found but too far inland / outside the river exception → rejected |
| `distance_km` | 919.9 |
| `geocode_agree` | True |
| `geocode_arbitration` | spatial_rejected |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Ketchikan official port of entry OR clearance OR "puerto habilitado" United States` |
| `seed_line` | `Ketchikan | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Ketchikan`, no GPS |

**Reading**

Triple problem: (1) listing USA group Alaska but mrgid 8456 = United States EEZ (mainland west coast), not Alaska 8463; (2) geocode OK but inland 920 km outside polygon 8456; (3) the place already exists in v1 and as `probable` as `Ketchikan Small Boat Harbor` (55.3431, -131.6467) on mrgid 8463. Another record `Ketchikan, Alaska` (8456) was judged `rejected`. Action: merge toward 8463, do not republish 8456.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu_mauvaise_zee` · confidence: **high**
- Correct mrgid: **8463** (Alaska)
- Merge target: `8463:ketchikansmallboatharbor`
- GPS: **55.3430696, -131.6466819** — Ketchikan Small Boat Harbor
- Sources:
  - poe_ports v1 Ketchikan Small Boat Harbor 55.3430696, −131.6466819 mrgid 8463
  - Nominatim Ketchikan 55.3430696, −131.6466819
  - 8456:ketchikanalaska unverified/rejected (do not republish)
- Note: slug usa→[8456,8463,8453] took the 1st. Inland 920 km outside the mainland EEZ. The place already exists in Alaska 8463. Merge. Do not correct 8456:ketchikan in place (collision / wrong polygon).

**Already in the database (same EEZ or nearby name)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| `poe_seed_ports` | Ketchikan, Alaska (mrgid **8456**) | unverified / rejected | None, None |
| v1 `poe_ports` | Ketchikan Small Boat Harbor (mrgid **8463** Alaska) | displayed on map | 55.3430696, -131.6466819 |
| `poe_seed_ports` | Ketchikan Small Boat Harbor (mrgid **8463**) | probable | 55.3430696, -131.6466819 |

---

### 33. Unalaska/Port of Dutch Harbor

**USA** · listing group `USA - Alaska` · `8456:unalaskaportofdutchharbor`

| Field | Value |
|---|---|
| `dedup_key` / `_id` | `8456:unalaskaportofdutchharbor` |
| `verify_verdict` | name_only |
| `listing_role` | `poe` (listing `is_port_of_entry: true`) |
| Listing country / slug | USA / `usa` |
| Listing group | USA - Alaska |
| `mrgid` / `zone_name` | 8456 / United States |
| VLIZ EEZ | United States — United States Exclusive Economic Zone (`iso2`=US, `pol_type`=200NM, sovereign=United States) |
| seed `country_iso2` | US |
| `seed_sources` | `listing` |
| `has_coords` / lat,lon | False / None, None |
| `validated` | False |
| Geocoded at | 2026-09-06T09:44:25Z |
| `geocode_query` | `Unalaska/Port of Dutch Harbor` |
| `spatial_kind` | `miss` — no usable Nominatim/GeoNames point |
| `distance_km` | — |
| `geocode_agree` | None |
| `geocode_arbitration` | — |
| `geocode_source` | *(null, coords not persisted)* |
| `judge_status` | *(absent — not judged)* |
| `search_query` | `Unalaska/Port of Dutch Harbor official port of entry OR clearance OR "puerto habilitado" United States` |
| `seed_line` | `Unalaska/Port of Dutch Harbor | listing:poe · verdict:name_only` |
| `built_at` | 2026-09-06T09:29:28Z |
| OSM | no tag / id / customs / border / port_of_entry / kinds |
| `source_urls` | none |
| Observations | 1 × listing (`extraction_engine: listing`), name `Unalaska/Port of Dutch Harbor`, no GPS |

**Reading**

Same EEZ error (8456 instead of 8463). v1 + `probable`: `Dutch Harbor Small Boat Harbor` (53.8831, -166.5525) on 8463. Merge.


**Verification** (2026-09-07)

- Decision: `fusion` · kind: `1_lieu_mauvaise_zee` · confidence: **high**
- Correct mrgid: **8463** (Alaska)
- Merge target: `8463:dutchharborsmallboatharbor`
- GPS: **53.8831064, -166.552545** — Dutch Harbor Small Boat Harbor
- Sources:
  - poe_ports v1 Dutch Harbor Small Boat Harbor 53.8831064, −166.552545 mrgid 8463
  - Nominatim Dutch Harbor, Unalaska 53.8867533, −166.5418000 (Alaska, not WA/MD)
- Note: Unalaska = the town, Dutch Harbor = the port, same island. Same 8456 vs 8463 bug. Merge toward v1 8463. 19 CFR: Dutch Harbor is a Customs station under Anchorage, not a stand-alone CBP PoE — the Noonsite listing still treats it as a yacht PoE.

**Already in the database (Alaska EEZ 8463)**

| Source | Name | Verdict / judge | lat, lon |
|---|---|---|---|
| v1 `poe_ports` | Dutch Harbor Small Boat Harbor | displayed on map | 53.8831064, -166.552545 |
| `poe_seed_ports` | Dutch Harbor Small Boat Harbor | probable | 53.8831064, -166.552545 |

---

## How to correct without breaking the inventory

1. For a merge: note the target `dedup_key` (v1/probable) and abandon
   the `name_only` record — or copy the target GPS onto the listing record then
   set the verdict to `confirmed` if listing + extract + coords.
2. For a new GPS: write `lat` / `lon` / `has_coords: true` on the
   `poe_seed_ports` document, **clear `geocoded_at`** only if you
   want enrich to re-geocode (otherwise set the point by hand and judge).
3. For a wrong EEZ: change `mrgid` **and** `dedup_key` (`{mrgid}:{normalized
   name}`), otherwise collision. Useful overrides:
   - Alaska → `8463`
   - Hawaii → `8453` (already)
   - Line Group / Kiritimati → `8441`
   - Andaman → `8333`
   - Svalbard / Longyearbyen → `33181` (to add in `slug_overrides` for `norway`)
4. Only then: `POST /api/poe/seeds/enrich` with
   `verdicts: ["name_only"]` **after** removing `geocoded_at` from
   the records to retry — or judge by hand (listing + GPS → `confirmed`
   without Claude if a v1/run/OSM extract is attached).
5. Forbidden: `POST /api/poe/seeds/build` (delete+insert of the whole
   collection).

## Other listing PoEs of the same group

Useful to know whether the listing means a *region* or a *port*.

| Record | Group | Other listing PoEs of the group |
|---|---|---|
| Geelong | Victoria (Australia) | Hastings, Melbourne (Australia), Portland |
| Newcastle and Port Stephen | New South Wales | Coffs Harbour, Port Kembla / Shellharbour, Sydney |
| Port Kembla / Shellharbour | New South Wales | Coffs Harbour, Newcastle and Port Stephen, Sydney |
| Big Creek / Placencia | — | Belize City, Punta Gorda, San Pedro (Ambergris Cay) |
| West End/Sopers Hole | Tortola | Road Harbour |
| Grand Mannan Harbour | New Brunswick | Caraquet, Dalhousie, Saint John |
| Marigot Bay (St Martin) | — | Anse Marcel, Oyster Pond - St Martin |
| Oyster Pond - St Martin | — | Anse Marcel, Marigot Bay (St Martin) |
| Marina Los Morros | — | Cayo Coco-Guillermo, Cienfuegos, Hemingway Marina, Marina Cayo Largo, Puerto de Vita, Santiago de Cuba, Varadero |
| Cassis | Mediterranean Coast (France) | Antibes, Bandol, Cannes, Fos, Hyères, La Ciotat, Le Lavandou, Marseille, Menton, Nice, … |
| Gironde Estuary & Bordeaux | Atlantic (France) | Brest, Hendaye, La Rochelle, Les Sables d’Olonne, Lorient, Nantes, St Nazaire |
| Christmas Island/Kiritimati | Line Islands | *(only PoE of the group)* |
| Tyrell Bay & Hillsborough | — | Prickly Bay, St George's |
| Barbers Point Harbour (Ko Olina) | Oahu | Honolulu |
| Andaman Islands | — | Cochin, Madras, Mumbai, Panaji |
| Bandar Bintan Telani (BBT) | Western Indonesia – Bintan… | Tanjung Pinang, Tarempa |
| Bowden Harbour/Port Morant | — | Kingston, Montego Bay, Ocho Rios, Port Antonio |
| Khuludhufushi | Upper North Province | *(only PoE of the group)* |
| Puerto Vallarta/ Banderas Bay | West Coast (Mexico) | Acapulco, Cabo, Ensenada, Huatulco, La Paz, Mazatlan, … |
| Colonia, Yap Island | Yap State | Ulithi Atoll |
| Lele/Leluh Harbour | Kosrae | Okat Harbour |
| Tanapag Harbour (Saipan) | — | *(only listing-country PoE)* |
| Longyearbyen | Svalbard (Spitsbergen) | *(only PoE of the group)* |
| San Carlos - Vista Mar Marina | Pacific (Panama) | Balboa, Mensabe, Pedregal, Puerto Mutis |
| Prince Edward Island | — | *(only listing-country PoE)* |
| Britannia Bay, Lovell | Mustique | *(only PoE of the group)* |
| Lata, Ndendo Island | Outer Islands/Atolls | *(only PoE of the group)* |
| Ria de Vigo and Baiona | North West Spain | Aviles, Bilbao, Finisterre, Gijon, Hondarribia, La Coruna, Santander |
| Cowes & R. Medina | South Coast | Dover, Falmouth, Plymouth, Portsmouth, Southampton Water |
| Oban/Dunstaffnage | Scotland | Largs, Peterhead |
| Ketchikan | USA - Alaska | Anchorage, Juneau, Unalaska/Port of Dutch Harbor |
| Unalaska/Port of Dutch Harbor | USA - Alaska | Anchorage, Juneau, Ketchikan |

## Machine file

- Raw export of the 33 Mongo documents: [`data/poe-name-only-33.json`](data/poe-name-only-33.json)
- Decisions of this review: [`data/poe-name-only-33-verifications.json`](data/poe-name-only-33-verifications.json)

## Constants of this snapshot

- Inventory: 4027 seeds; remaining `name_only`: **33**
- `poe_ports` (displayed v1 map): **1280** — not modified
- Claude credit of the run: not consumed on these 33 (geocode only)
