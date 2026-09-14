# Climatology snapshots

Generated **off the VPS** (see `scripts/climatology/`). The server only
reads them. While a product is missing, the API returns `null` / an
empty FeatureCollection — it does not invent a field.

| Folder | Files | Source |
|--------|-------|--------|
| `cyclones/` | `ibtracs_since1980.json` | IBTrACS v04r01 |
| `wind/` | `wind-MM.npz` + `.atlas.json` | CMEMS WIND MY L4 |
| `wave/` | `wave-MM.npz` | WAVERYS |
| `current/` | `current-MM.npz` | GLORYS12 climatology_P1M-m |

`kind: "climatology"` everywhere. Not for navigation.
