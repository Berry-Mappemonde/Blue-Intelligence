"""OSM-shaped + sentinel-pilot source, without depending on the backend."""

PILOT_SOURCE = "sentinel-pilot"
DISCLAIMER = (
    "Not for navigation. Estimated line / depth "
    "(Sentinel pilot), compare with official charts."
)


def stamp_features(fc: dict, dataset: str) -> dict:
    out = dict(fc)
    feats = []
    for i, feat in enumerate(fc.get("features") or []):
        item = dict(feat)
        p = dict(item.get("properties") or {})
        p["source"] = PILOT_SOURCE
        p.setdefault("disclaimer", DISCLAIMER)
        p.setdefault("provider", "CDSE / pilote corridor")
        if "depth" in dataset or p.get("seamark:type") == "depth_area":
            p.setdefault("seamark:type", "depth_area")
            p.setdefault("kind", "depth_area")
            p.setdefault("name", "Zone de profondeur Sentinel (pilote)")
        else:
            p.setdefault("natural", "coastline")
            p.setdefault("kind", "coastline")
            p.setdefault("name", "Trait de côte Sentinel (pilote)")
        p.setdefault("id", p.get("native_id") or f"{dataset}-{i}")
        item["properties"] = p
        feats.append(item)
    out["features"] = feats
    return out
