# Reference catalogue of `seamark:*` tags and usable harbour tags

Inspired by the [Open Waters: Seamap](https://github.com/openwatersio/seamap)
repository (`src/main/java/Seamark.java`, `bin/audit-tags.ts`): document in
black and white **what our pipelines read** in OpenStreetMap, and what remains
usable tomorrow. The machine version is `backend/data/seamark_catalog.json`,
consumed by `scripts/audit_tags.py`.

Golden rule inherited from Blue Intelligence: **we invent nothing**. A missing
tag stays missing; a badge, a phone number or a VHF channel appears only if a
tag attests it.

This catalogue is an **OpenSeaMap export target** (BI fields ← OSM tags),
not an S-101 encoder. See `docs/archives/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.

## How to read this catalogue

- **used** — read today by a pipeline (marina dump, harbour masters,
  service badges, enrichment).
- **candidate** — documented here, usable in a future iteration; the
  audit report measures its real presence in our data.
- The audit (`python scripts/audit_tags.py`) compares this catalogue to
  real Mongo data and lists keys **outside the catalogue**: it is a report,
  not a CI check — real OSM data contains typos, a human eye decides
  (see `docs/audits/`).

## Marinas mode

| Tag | Status | Usage |
|---|---|---|
| `leisure=marina` | used | identity of the world dump |
| `seamark:type=harbour` + `seamark:harbour:category` | used | category (marina, yacht_harbour…) — 68% of records |
| `seamark:harbour:capacity`, `capacity` | used | **Berthing** badge |
| `seamark:harbour:draught`, `max_depth`, `depth` | used | **Berthing** badge (draught) |
| `mooring` | used | **Berthing** badge |
| `fuel`, `drinking_water`, `electricity`, `shop` | used | **Provisioning** badge |
| `seamark:small_craft_facility:category` | used | badge by value (fuel → Provisioning, slipway/crane/boat_hoist/pump_out → Technical, toilets/showers/laundrette → Ashore, visitor_berth → Berthing) |
| `pumpout`, `sanitary_dump_station`, `waste_disposal` | used | **Technical** badge |
| `shower`, `toilets`, `restaurant`, `wifi`, `internet_access`, `wheelchair` | used | **Ashore** badge |
| `website`, `contact:website`, `url` | used | official site (tier-2 verified) |
| `phone`, `contact:phone`, `email`, `contact:email`, `opening_hours`, `operator`, `fee`, `charge`, `description` | used | record |
| `seamark:type=berth` + `seamark:berth:category` | candidate | visitor berths at the quay |
| `seamark:type=harbour_basin`, `dock`, `marina` (frequent typo) | candidate | variants observed by the audit |

## Harbour masters mode

| Tag | Status | Usage |
|---|---|---|
| `office=harbour_master`, `seamark:building:function=harbour_master`, `harbour=harbour_master` | used | identity |
| `phone`, `contact:phone`, `telephone`, `mobile`, `contact:mobile` | used | phone (never invented) |
| `vhf`, `vhf_channel`, `channel`, `harbour:vhf`, `communication:vhf`, `seamark:communication:channel`, `seamark:harbour:vhf`, `comcha`, `shom:comcha` | used | VHF channel |
| `seamark:information`, `inform`, `ninfom`, `note`, `shom:*`, `noaa:*` | used | notes / SHOM & NOAA overlay |

## Anchorages mode (route corridor)

| Tag | Status | Usage |
|---|---|---|
| `seamark:type=anchorage` + `seamark:anchorage:category` | used | anchorage zones — `anchorage_build.py` |
| `seamark:type=anchor_berth` | used | numbered berths |
| `seamark:type=mooring` + `seamark:mooring:category` | used | buoys / mooring buoys |
| `natural=bay` (named) | used | natural bay along the corridor |
| `seamark:type=restricted_area` + `seamark:restricted_area:restriction=no_anchoring` | candidate | anchoring forbidden — MPA overlay |

## Reverse mapping (slim BI field → OSM export tags)

Machine table: `export_mapping` in `seamark_catalog.json`. Example: **Provisioning** badge / `fuel` field → `fuel=yes` + `seamark:small_craft_facility:category=fuel`. Allowed direction: OSM → BI fields → OSM GeoJSON. No S-101 attributes.

## Satellite pilots (Science mode, before the first dump)

| Tag | Status | Usage |
|---|---|---|
| `natural=coastline` | candidate | MNDWI / CoastSat coastline (Berry corridor) |
| `seamark:type=depth_area` | candidate | Stumpf SDB classes — not a DTM, not an ENC |

## NAVIGUIDE route (landfalls, hazards)

| Tag | Status | Usage |
|---|---|---|
| `seamark:type=light` + `character/colour/period/range` | candidate | landfall lights at stops (`Fl(3)WRG.10s`) |
| `seamark:type=rock` / `wreck` / `obstruction` | candidate | hazards along the corridor |

## Adding a tag to the catalogue

1. Run the audit: `python scripts/audit_tags.py --out docs/audits/$(date +%F)-tags.md`.
2. Look at the “outside catalogue” / “undocumented sub-keys” sections;
   watch for OSM typos (`seamark:type=no`, `marina`…), that is exactly the
   role of the human eye.
3. Add the entry in `backend/data/seamark_catalog.json` (status
   `candidat`, then `exploite` when a pipeline actually reads it).
4. Update this document and, if the tag feeds a badge, the
   `SERVICE_TAG_QUESTIONS` table in `backend/app/services/marina_world.py`.

## References

- [OpenSeaMap — Seamark tag values](https://wiki.openstreetmap.org/wiki/OpenSeaMap/Seamark_Tag_Values)
- [openwatersio/seamap](https://github.com/openwatersio/seamap) — `Seamark.java`, `SeamarkZoomRules.java`, `bin/audit-tags.ts`
- `backend/app/services/marina_build.py` (`KEPT_TAGS`) and `capitainerie_world.py` (`kept_tags`)
