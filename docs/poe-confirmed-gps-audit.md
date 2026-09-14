# GPS audit of `confirmed` seeds

Step of 2026-09-07. **No rebuild** (`POST /api/poe/seeds/build` is forbidden).
**No batch** of `unverified` / `probable` until the remaining flags have been
re-read. Touch the 781 `confirmed` records **only** for a clearly wrong GPS.
Tanjung Pinang and Bandar Bintan Telani remain two distinct marinas.

Machine export: [`data/poe-confirmed-gps-audit.json`](data/poe-confirmed-gps-audit.json).

## Method

On the **781** geocoded `confirmed` records, offline:

1. **Reclassify** the GPS against the VLIZ polygon (`spatial_class_for_point`).
   - `inland_far`: `inland_river` > 30 km, or `inland` / `other_water` > 8 km
   - `outside_eez_far`: outside the polygon and far from the coast (same 30 km
     threshold for `inland_river`, so as not to drown Shanghai / Bristol)
2. **`homonym_paren_mismatch`**: the name (or `listing_name`) has a parenthesis
   (Bintan Island, Oregon, Georgia…) whose tokens do not match the GPS.
   Suggestion = **island centroid** (Bintan 1.08°N / 104.42°E), never the GPS
   of another marina (not Bandar Bintan Telani).
3. **`listing_group_outlier`**: isolated > 300 km from the *healthy* cluster
   (in_eez / coastal) of the same `listing_group` + `mrgid`. A confirmed record
   already in_eez is flagged only if it is > 1,500 km (Astoria NY vs west coast).
4. **`nominatim_inland_listing_only`**: `seed_sources=["listing"]`,
   `geocode_source=nominatim`, GPS inland > 30 km.

`verify_verdict` / `confirmation_status` do not change.

### Automatic corrections (obvious cases only)

- **Tanjung Pinang**: Nominatim took the Sumatra village (Palembang), not
  Bintan. Bintan centroid, `geocode_source=manual_audit`.
- Any `confirmed` spatially off the coast **and** > 30 km **for which an
  in_eez observation of the same `name_norm` exists**: take that GPS,
  `geocode_source=observation`.

If a homonym remains possible (St-Nazaire Gard vs Loire-Atlantique, Astoria NY
vs Oregon, Safi, Gabes, Savannah without a coastal observation): **flag only**,
no `lat`/`lon` change.

`poe_ports` (1280) is modified only if the same `dedup_key` there carries **the
same** aberrant GPS. Log: `poe_audit_log.action = gps_audit_correct`.

Code: `backend/app/services/poe_confirmed_gps_audit.py`.
Workshop API: `GET /api/poe/seeds/gps-audit` (dry-run).
Script: `python3 backend/scripts/audit_confirmed_gps.py [--persist]`.

## Atlas result (2026-09-07T08:01:30Z)

Before / after persist:

| | before | after |
|---|---:|---:|
| `poe_seed_ports` | 4034 | 4034 |
| `poe_ports` | 1280 | 1280 |
| `confirmed` | 781 | 781 |
| `gps_audit_status=corrected` | 0 | **4** |
| `gps_audit_status=flagged` | 0 | **16** |
| `gps_audit_status=ok` | 0 | 761 |
| `poe_ports` patched (same key + same aberrant GPS) | — | 3 |
| key merges | 0 | 0 |

20 flags at scan (13 high, 7 medium); 4 obvious corrections.

### Corrected

| Key | Name | GPS before | GPS after | Source |
|---|---|---|---|---|
| `8492:tanjungpinangbintanislandriauislands` | Tanjung Pinang (Bintan Island) | −3.356 / 104.657 (Sumatra) | **1.08 / 104.42** (Bintan centroid) | `manual_audit` |
| `8429:ensenada` | Ensenada | 24.06 / −106.70 | 31.85 / −116.63 (Baja) | `observation` |
| `8429:lapaz` | La Paz | 19.35 / −98.96 | 24.16 / −110.33 (BCS) | `observation` |
| `5675:parnu2parnuport` | Pärnu 2 (Pärnu Port) | 57.77 / 26.03 (inland) | 58.38 / 24.50 (coast) | `observation` |

The last three already existed in `poe_ports` with the same aberrant GPS:
corrected as well, count 1280 unchanged. Tanjung Pinang was not in
`poe_ports` (listing-only).

### Corrected later (UN/LOCODE / authority research)

15 GPS points settled, `geocode_source=manual_audit`. No key merges.
No group centroid (Savannah ≠ Delaware, Vancouver ≠ Prince Rupert).

**PR-revisable** source of truth: [`data/poe-gps-arbitrated.json`](data/poe-gps-arbitrated.json)
(plus a Python dict). Loader: `backend/app/services/poe_gps_registry.py`.
Workshop: `GET /api/poe/seeds/gps-arbitrated` (git read, no persist).

| Key | Name | GPS before | GPS after |
|---|---|---|---|
| `8456:savannah` | Savannah | Finger Lakes NY | **32.08 / −81.09** (USSAV) |
| `8456:astoria` | Astoria | Queens NY | **46.19 / −123.83** (Oregon) |
| `5677:stnazaire` | St Nazaire | Gard | **47.28 / −2.20** (FRSNR). Key `nantessaintnazaire` unchanged |
| `8367:safi` | Safi | hinterland | **32.31 / −9.25** (MASFI) |
| `8366:gabes` | Gabes | hinterland | **33.91 / 10.10** (TNGAE) |
| `8479:portofmtwara` | Port of Mtwara | 86 km inland | **−10.27 / 40.20** (TZMYW) |
| `8479:portoftanga` | Port of Tanga | 82 km inland | **−5.07 / 39.11** (TZTGT) |
| `8464:recife` | Recife | Paraná | **−8.06 / −34.87** (BRREC) |
| `8493:vancouver` | Vancouver | Gold River / Nootka | **49.29 / −123.11** (Canada Place) |
| `8456:brunswick` | Brunswick | NY inland | **31.13 / −81.54** (Georgia) |
| `8484:tpdanang` | Tp Da Nang | Quảng Nam inland | **16.10 / 108.23** (VNDAD) |
| `5697:canakkale` | Çanakkale | hinterland | **40.10 / 26.38** (Kepez) |
| `5697:mersin` | Mersin | hinterland Mut | **36.80 / 34.64** (TRMER) |
| `8349:portofkilifi` | Port of Kilifi | hinterland | **−3.64 / 39.86** (Kilifi Creek) |
| `8324:portofmadang` | Port of Madang | −5.0 / 145.5 | **−5.21 / 145.80** (PGMAG) |

`5693:puertodemelilla`: GPS already on the quay (~400 m from Wikipedia). VLIZ
false positive (enclave). Registry `action=keep` → `gps_audit_status=ok`,
lat/lon unchanged.

Sidney BC (`8493:portofsidney`): **ok**, not flagged despite Sydney NS observations.

## Homonym scorer (geocoding)

`geocode_port_dual` / `pick_geocode` score up to **10** candidates (Nominatim
net; the system is parentheses, `listing_group`, pairs, and the JSON registry):

- parentheses kept in the query (Bintan before Sumatra)
- VLIZ polygon of **this** mrgid + OSM harbour class
- `listing_group` as a filter (West Coast USA → lon < −90°), never a GPS to copy
- coastal pairs of the same group: proximity, not merge
- two basins with close scores **without** a hint → `geocode_status=ambiguous`,
  no GPS is set (and an existing GPS is not overwritten)
- `geocode_one` consults the `accepted` registry **before** Nominatim
  (`geocode_arbitration=gps_registry`). Claude does not pick a point.

`_needs_geocode`: `name_only` without a point, or `inland_far` / `ambiguous`.
Confirmed `ok` / `corrected` records are **not** re-geocoded.

17 `unverified` inland_far records were re-geocoded with the scorer (Ibiza Madrid →
Ibiza, Semarang, Huatulco, Punta Cana, etc.). Three returns: **Sevilla**
(Guadalquivir river port), **Kingston** (Newfoundland jump), **Hokkaido**
(island, not Sapporo). The scorer now rejects a distant quay whose label is
not the toponym, and a listing pair more than 1,500 km away.

## Tanjung Pinang — before / after

Nominatim returned the village *Tanjung Pinang, Ogan Ilir, Sumatera Selatan*
(−3.36 / 104.66) instead of the city *Tanjungpinang, Kepulauan Riau*
(~0.92 / 104.45). The Claude judge had said YES (Bintan texts). The GPS was
wrong.

| | lat | lon | source | spatial |
|---|---:|---:|---|---|
| Before | −3.3564491 | 104.6571166 | nominatim | inland_river 40.8 km |
| After | **1.08** | **104.42** | manual_audit | in_eez (sliver 1.4 km) |
| Bandar Bintan Telani (unchanged) | 1.1605006 | 104.3201677 | — | — |
| name_only `…bbtbintanisland` | — | — | — | still name_only, not merged |

The suggestion is **not** the GPS of Bandar Bintan Telani (another marina,
1.1605 / 104.3202).

## What we are not doing now

- `POST /api/poe/seeds/build`
- Enrich `unverified` / `probable` (~1,805) — only the
  `inland_far` / `ambiguous` seeds, not the 781 confirmed ok
- Key merges

**Next step**: `unverified` batch (excluding confirmed ok).
