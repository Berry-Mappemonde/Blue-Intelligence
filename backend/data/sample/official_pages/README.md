# Official page snapshots (sample mode)

Small verbatim excerpts of real official pages, used by `evidence_store.lookup` in
`SAMPLE_MODE` (or when Mongo is unreachable) so that a fresh clone can show official
evidence without credentials. Sample mode runs the same grounding over these files
as generation runs over freshly fetched pages.

Each file holds the page `url`, `fetched_at`, the `sha256` and length (`chars`) of the
**full** text fetched by `app.core.extract.extract_cascade`, the extraction level, the
zones it applies to, and `sections`: exact slices of that text (`offset` into it, then
the text), cut at line breaks around the relevant passage. Text is never edited.
`designates` lists the ports the page names as an entry or clearance point.

| File | Page | Why it qualifies |
| --- | --- | --- |
| `bm_gov_customs_department.json` | <https://www.gov.bm/department/customs> | Lists St. George's and Hamilton among Bermuda's main ports of entry, where customs officers are stationed |
| `bm_planning_scoping_report.json` | <https://planning.gov.bm/wp-content/uploads/2018/11/Scoping-Report.pdf> | States that St. George's harbour is the requisite port of call for clearing Customs for non-commercial vessels |
| `ag_customs_temporary_importation.json` | <https://customs.gov.ag/page/temporary-importation> | Lists Deep water Harbor first among Antigua and Barbuda's legal ports of entry for pleasure craft |
| `bs_customs_about_us_ports_of_entry.json` | <https://www.bahamascustoms.gov.bs/accordions/about-ecas-2/> | Lists Conch Inn Marina under the Marsh Harbour, Abaco ports of entry |
| `us_cbp_alaska_pleasure_boat_locations.json` | <https://www.cbp.gov/travel/pleasure-boats-private-flyers/pleasure-boat-locations/ak> | Names Anchorage Small Boat Harbor as Anchorage's designated marina for CBP arrival inspection |

Only pages that designate a port were kept. Fetched pages that name a port without
designating it were left out: contact listings (Barbados Immigration, Bosnia and
Herzegovina's Tuzla office, Bermuda's customs declaration notice), budget and
statistics documents (Angola). Zones without a qualifying page stay at their
registry tier.
