"""Stock du voyage officiel — une interface, deux dos (lot RF2, D5').

Même API (« donne-moi le script / les moments / l'ETA… ») ; derrière :
MongoDB (base ``naviguide_simulator``) si ``SIMULATOR_MONGO_URL`` est posé,
fichiers sur disque sinon. Jamais ``MONGO_URL_LOCAL`` ni ``DB_NAME``.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger("naviguide-simulator.official-store")

FAMILIES = ("moments", "film", "eta", "climo", "ici", "plan_review")
STATUS_PREPARING = "preparing"
STATUS_READY = "ready"
MONGO_DB = "naviguide_simulator"
MONGO_COL = "official_voyage"
DEFAULT_ROUTE = "berry-mappemonde-2026-officiel"
DEFAULT_T0 = "2026-05-15T08:00:00Z"
WORKER_PERIOD_S = 300.0

_LOCK = threading.Lock()
_STORE: Optional["OfficialStore"] = None
_WORKER_STARTED = False
_FILL_GEN: dict[str, int] = {f: 0 for f in FAMILIES}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(when: Optional[datetime] = None) -> str:
    return (when or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def data_date(when: Optional[datetime] = None) -> str:
    forced = (os.environ.get("NAVIGUIDE_OFFICIAL_DATA_DATE") or "").strip()
    if forced:
        return forced[:10]
    return (when or _now()).strftime("%Y-%m-%d")


def make_key(
    route_id: str = DEFAULT_ROUTE,
    t0: str = DEFAULT_T0,
    date: Optional[str] = None,
) -> str:
    return f"{route_id}|{t0}|{date or data_date()}"


def current_key() -> str:
    return make_key()


def _safe_key(key: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in key)[:180]


def default_disk_dir() -> Path:
    env = (os.environ.get("NAVIGUIDE_OFFICIAL_STORE_DIR") or "").strip()
    if env:
        return Path(env)
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("CI"):
        return Path(os.environ.get("TMPDIR") or "/tmp") / "naviguide-official-store"
    return Path.home() / ".cache" / "naviguide" / "voyage-store"


class DiskBackend:
    """Dos fichiers : un JSON par (clé, famille), remplacement atomique."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else default_disk_dir()

    def _path(self, key: str, family: str) -> Path:
        return self.root / f"{_safe_key(key)}__{family}.json"

    def get(self, key: str, family: str) -> Optional[dict]:
        dest = self._path(key, family)
        if not dest.is_file():
            return None
        try:
            return json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("stock disque illisible %s: %s", dest, exc)
            return None

    def put(self, key: str, family: str, entry: dict) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        dest = self._path(key, family)
        tmp = dest.with_suffix(".tmp")
        payload = json.dumps(entry, ensure_ascii=False, indent=0)
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(dest)
        return entry


class MongoBackend:
    """Dos Mongo : base ``naviguide_simulator`` seulement. Client injectable (tests)."""

    def __init__(self, url: str, client: Any = None):
        self.url = url
        self._client = client
        self._col = None

    def _collection(self):
        if self._col is not None:
            return self._col
        if self._client is None:
            from pymongo import MongoClient  # noqa: PLC0415

            self._client = MongoClient(self.url, serverSelectionTimeoutMS=2500)
        self._col = self._client[MONGO_DB][MONGO_COL]
        return self._col

    def get(self, key: str, family: str) -> Optional[dict]:
        doc = self._collection().find_one({"_id": f"{key}:{family}"})
        if not doc:
            return None
        out = {k: v for k, v in doc.items() if k != "_id"}
        return out

    def put(self, key: str, family: str, entry: dict) -> dict:
        doc = {"_id": f"{key}:{family}", **entry}
        self._collection().replace_one({"_id": doc["_id"]}, doc, upsert=True)
        return entry


class FakeMongoClient:
    """Double de test (même surface que mongomock : ``client[db][col]``)."""

    def __init__(self, *args: Any, **kwargs: Any):
        self._dbs: dict[str, "_FakeDb"] = {}

    def __getitem__(self, name: str) -> "_FakeDb":
        return self._dbs.setdefault(name, _FakeDb())

    def close(self) -> None:
        return None


class _FakeDb:
    def __init__(self):
        self._cols: dict[str, "_FakeCol"] = {}

    def __getitem__(self, name: str) -> "_FakeCol":
        return self._cols.setdefault(name, _FakeCol())


class _FakeCol:
    def __init__(self):
        self._docs: dict[str, dict] = {}

    def find_one(self, query: dict, *args: Any, **kwargs: Any) -> Optional[dict]:
        doc = self._docs.get((query or {}).get("_id"))
        return copy.deepcopy(doc) if doc else None

    def replace_one(self, query: dict, doc: dict, upsert: bool = True) -> Any:
        self._docs[query["_id"]] = copy.deepcopy(doc)
        return type("R", (), {"acknowledged": True, "modified_count": 1})()


def mongo_test_client() -> Any:
    """mongomock si présent, sinon le double local — jamais une vraie base."""
    try:
        import mongomock  # noqa: PLC0415

        return mongomock.MongoClient()
    except ImportError:
        return FakeMongoClient()


class OfficialStore:
    """Une seule interface. Le dos se choisit à la construction."""

    def __init__(self, backend: Any):
        self.backend = backend

    def get(self, family: str, key: Optional[str] = None) -> Optional[dict]:
        if family not in FAMILIES:
            raise ValueError(family)
        with _LOCK:
            return self.backend.get(key or current_key(), family)

    def put(self, family: str, payload: Any, key: Optional[str] = None) -> dict:
        if family not in FAMILIES:
            raise ValueError(family)
        k = key or current_key()
        entry = {
            "key": k,
            "family": family,
            "storedAt": _iso(),
            "dataDate": k.rsplit("|", 1)[-1],
            "payload": payload,
        }
        with _LOCK:
            self.backend.put(k, family, entry)
        return entry

    def payload(self, family: str, key: Optional[str] = None) -> Optional[Any]:
        entry = self.get(family, key=key)
        if not entry:
            return None
        return entry.get("payload")


def _choose_backend(
    *,
    disk_dir: Optional[Path] = None,
    mongo_url: Optional[str] = None,
    mongo_client: Any = None,
) -> Any:
    url = (mongo_url if mongo_url is not None else os.environ.get("SIMULATOR_MONGO_URL") or "").strip()
    if url:
        return MongoBackend(url, client=mongo_client)
    return DiskBackend(disk_dir)


def reset() -> None:
    global _STORE
    with _LOCK:
        _STORE = None
        for fam in FAMILIES:
            _FILL_GEN[fam] = 0


def configure(
    *,
    backend: Any = None,
    disk_dir: Optional[Path] = None,
    mongo_url: Optional[str] = None,
    mongo_client: Any = None,
) -> OfficialStore:
    global _STORE
    store = OfficialStore(backend or _choose_backend(
        disk_dir=disk_dir, mongo_url=mongo_url, mongo_client=mongo_client,
    ))
    with _LOCK:
        _STORE = store
    return store


def get_store() -> OfficialStore:
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = OfficialStore(_choose_backend())
        return _STORE


def fill_generation(family: str) -> int:
    return int(_FILL_GEN.get(family) or 0)


def preparing_moments(until: Optional[str] = None) -> dict:
    return {
        "voyageId": DEFAULT_ROUTE,
        "until": until,
        "count": 0,
        "moments": [],
        "status": STATUS_PREPARING,
    }


def preparing_film(seconds: int = 150) -> dict:
    return {
        "status": STATUS_PREPARING,
        "chapters": [],
        "source": "store",
        "chars": 0,
        "targetSeconds": seconds,
        "hasWritten": False,
    }


def preparing_eta(now: Optional[datetime] = None) -> dict:
    when = now or _now()
    return {
        "p10": None,
        "p50": None,
        "p90": None,
        "members": 0,
        "source": None,
        "computedAt": _iso(when),
        "memberKnots": [],
        "status": STATUS_PREPARING,
        "reason": STATUS_PREPARING,
        "lastAttempt": None,
        "nextRetry": None,
    }


def preparing_clock() -> dict:
    return {"status": STATUS_PREPARING}


def preparing_review() -> dict:
    return {
        "status": STATUS_PREPARING,
        "voyageId": DEFAULT_ROUTE,
        "legs": [],
        "pearlsUnknown": 0,
        "comment": {"text": "", "source": "store", "cached": True},
    }


def preparing_ici(lat: float, lon: float, radius_nm: float = 30.0) -> dict:
    try:
        from ici_engine import empty_dossier  # noqa: PLC0415

        bag = empty_dossier(lat, lon, radius_nm)
    except Exception:
        bag = {"at": {"lat": lat, "lon": lon}, "zee": None, "poe": [], "amp": []}
    bag["status"] = STATUS_PREPARING
    return bag


def official_clock() -> Optional[dict]:
    payload = get_store().payload("climo")
    if not isinstance(payload, dict):
        return None
    clock = payload.get("clock")
    if isinstance(clock, dict) and clock.get("t0") and clock.get("vertices"):
        return clock
    return None


def official_moments(until: Optional[str] = None) -> Optional[dict]:
    payload = get_store().payload("moments")
    if not isinstance(payload, dict):
        return None
    rows = list(payload.get("moments") or [])
    if until:
        cut = str(until)
        rows = [row for row in rows if str(row.get("t") or "")[: len(cut)] <= cut]
    out = {
        "voyageId": payload.get("voyageId") or DEFAULT_ROUTE,
        "until": until,
        "count": len(rows),
        "moments": rows,
        "status": STATUS_READY,
    }
    if payload.get("journal"):
        out["journal"] = payload["journal"]
    return out


def official_journal() -> Optional[dict]:
    payload = get_store().payload("moments")
    if not isinstance(payload, dict):
        return None
    journal = payload.get("journal")
    return journal if isinstance(journal, dict) else None


def _norm_stop(name: str) -> str:
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def official_eta(stop: str) -> Optional[dict]:
    payload = get_store().payload("eta")
    if not isinstance(payload, dict):
        return None
    stops = payload.get("stops") if isinstance(payload.get("stops"), dict) else payload
    if not isinstance(stops, dict):
        return None
    wanted = _norm_stop(stop)
    if stop in stops and isinstance(stops[stop], dict):
        return dict(stops[stop])
    for name, row in stops.items():
        if name in FAMILIES or name in ("status", "stops"):
            continue
        if isinstance(row, dict) and (
            _norm_stop(name) == wanted
            or wanted in _norm_stop(name)
            or _norm_stop(name) in wanted
        ):
            return dict(row)
    return None


def official_plan_review() -> Optional[dict]:
    payload = get_store().payload("plan_review")
    return dict(payload) if isinstance(payload, dict) else None


def official_film(lang: str = "fr", seconds: int = 150) -> Optional[dict]:
    payload = get_store().payload("film")
    if not isinstance(payload, dict):
        return None
    films = payload.get("films") if isinstance(payload.get("films"), dict) else payload
    if not isinstance(films, dict):
        return None
    lg = (lang or "fr")[:2].lower()
    for slot in (f"{lg}:{int(seconds)}", f"{lg}:150", f"{lg}:0", "fr:150"):
        row = films.get(slot)
        if isinstance(row, dict) and (row.get("chapters") or row.get("status") == STATUS_READY):
            return dict(row)
    if films.get("chapters"):
        return dict(films)
    return None


def apply_film_t0(payload: dict, t0: Optional[str]) -> dict:
    """Réécrit les dates affichées du script stocké — pas un recalcul météo."""
    if not t0 or not isinstance(payload, dict):
        return payload
    try:
        from film_script import day_month, resolve_film_t0  # noqa: PLC0415
        from voyage_clock import OFFICIAL_T0, parse_iso  # noqa: PLC0415
    except Exception:
        return payload
    want = resolve_film_t0(t0)
    if want == OFFICIAL_T0:
        return payload
    try:
        old_dt = parse_iso(OFFICIAL_T0)
        new_dt = parse_iso(want)
    except Exception:
        return payload
    out = copy.deepcopy(payload)
    for lang in ("fr", "en"):
        old = day_month(old_dt, lang, year=True)
        new = day_month(new_dt, lang, year=True)
        if not old or old == new:
            continue
        for ch in out.get("chapters") or []:
            text = ch.get("text")
            if isinstance(text, str) and old in text:
                ch["text"] = text.replace(old, new)
    return out


def official_ici(lat: float, lon: float, max_nm: float = 12.0) -> Optional[dict]:
    payload = get_store().payload("ici")
    if not isinstance(payload, dict):
        return None
    bags = payload.get("bags") or []
    best = None
    best_d = float("inf")
    try:
        from isochrone import haversine  # noqa: PLC0415
    except Exception:
        return None
    for row in bags:
        if not isinstance(row, dict):
            continue
        bag = row.get("bag") if isinstance(row.get("bag"), dict) else row
        at = bag.get("at") if isinstance(bag.get("at"), dict) else {}
        blat = at.get("lat") if at.get("lat") is not None else row.get("lat")
        blon = at.get("lon") if at.get("lon") is not None else row.get("lon")
        if not isinstance(blat, (int, float)) or not isinstance(blon, (int, float)):
            continue
        d = haversine(lat, lon, float(blat), float(blon))
        if d < best_d:
            best_d = d
            best = bag
    if best is not None and best_d <= max_nm:
        return dict(best)
    return None


def on_official_route(lat: float, lon: float, max_nm: float = 8.0) -> bool:
    try:
        from isochrone import haversine  # noqa: PLC0415
        from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
        from voyage_store import load_voyage  # noqa: PLC0415
    except Exception:
        return False
    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    pts = (voy or {}).get("points") or []
    if not pts:
        clock = official_clock() or {}
        pts = clock.get("vertices") or []
    step = max(1, len(pts) // 80) if pts else 1
    for p in pts[::step]:
        plat, plon = p.get("lat"), p.get("lon")
        if isinstance(plat, (int, float)) and isinstance(plon, (int, float)):
            if haversine(lat, lon, float(plat), float(plon)) <= max_nm:
                return True
    return False


def seed_payloads() -> dict[str, Any]:
    """Contenu disque du poste de recette : Journal, fourchette, revue, film."""
    t0 = DEFAULT_T0
    moments = [
        {
            "voyageId": DEFAULT_ROUTE,
            "seq": 0,
            "t": t0,
            "pos": {"lat": 46.8075, "lon": 1.6358},
            "signature": "depart-saint-maur",
            "changes": [{
                "kind": "escale", "score": 3, "title": "Départ",
                "fact": "Saint-Maur-des-Fossés",
            }],
            "moment": {
                "t": t0,
                "pos": {"lat": 46.8075, "lon": 1.6358},
                "here": {"zee": {"name": "France"}},
                "leg": {"to": "La Rochelle", "regime": "climatology"},
                "alerts": [],
                "around": [],
            },
        },
        {
            "voyageId": DEFAULT_ROUTE,
            "seq": 1,
            "t": "2026-05-15T12:00:00Z",
            "pos": {"lat": 46.15, "lon": -1.16},
            "signature": "escale-la-rochelle",
            "changes": [{
                "kind": "escale", "score": 3, "title": "La Rochelle",
                "fact": "arrivée",
            }],
            "moment": {
                "t": "2026-05-15T12:00:00Z",
                "pos": {"lat": 46.15, "lon": -1.16},
                "here": {"zee": {"name": "France"}},
                "leg": {"to": "Fort-de-France (Martinique)", "regime": "climatology"},
                "alerts": [],
                "around": [],
            },
        },
    ]
    film_fr = {
        "status": STATUS_READY,
        "source": "rules",
        "chars": 120,
        "targetSeconds": 150,
        "hasWritten": False,
        "chapters": [{
            "id": "ch-0",
            "fromName": "Saint-Maur-des-Fossés",
            "toName": "La Rochelle",
            "fromLat": 46.8075,
            "fromLon": 1.6358,
            "toLat": 46.15,
            "toLon": -1.16,
            "text": "Le 15 mai 2026, le bateau quitte Saint-Maur-des-Fossés vers La Rochelle.",
            "events": [{"score": 3, "kind": "stop", "title": "Départ"}],
        }],
    }
    film_en = {
        **copy.deepcopy(film_fr),
        "chapters": [{
            **film_fr["chapters"][0],
            "text": "On 15 May 2026 the boat left Saint-Maur-des-Fossés for La Rochelle.",
        }],
    }
    eta_row = {
        "p10": "2026-10-11T00:00:00Z",
        "p50": "2026-10-12T12:00:00Z",
        "p90": "2026-10-14T00:00:00Z",
        "members": 24,
        "memberKnots": [8.0, 8.2, 7.9],
        "source": "store",
        "computedAt": _iso(),
        "status": STATUS_READY,
    }
    clock = {
        "t0": t0,
        "kind": "climatology",
        "vertices": [
            {
                "tHours": 0, "sailNm": 0, "filmNm": 0, "lat": 46.8075, "lon": 1.6358,
                "iso": t0, "speedKnots": 0, "vehicle": "quay",
            },
            {
                "tHours": 4, "sailNm": 0, "filmNm": 80, "lat": 46.15, "lon": -1.16,
                "iso": "2026-05-15T12:00:00Z", "speedKnots": 7.0, "vehicle": "main",
            },
            {
                "tHours": 3000, "sailNm": 8200, "filmNm": 8280, "lat": -22.27, "lon": 166.44,
                "iso": "2026-09-17T08:00:00Z", "speedKnots": 6.5, "vehicle": "main",
            },
        ],
        "marks": [
            {"name": "Saint-Maur-des-Fossés", "nm": 0, "filmNm": 0, "lat": 46.8075, "lon": 1.6358, "index": 0},
            {"name": "La Rochelle", "nm": 0, "filmNm": 80, "lat": 46.15, "lon": -1.16, "index": 1},
            {"name": "Nouméa", "nm": 8200, "filmNm": 8280, "lat": -22.27, "lon": 166.44, "index": 2},
        ],
    }
    review = {
        "status": STATUS_READY,
        "voyageId": DEFAULT_ROUTE,
        "generatedAt": _iso(),
        "legs": [{
            "from": "La Rochelle",
            "to": "Fort-de-France (Martinique)",
            "fromNm": 0,
            "toNm": 3350,
            "legNm": 3350,
            "daysAtSea": 18,
            "holdDays": 3,
            "month": 5,
            "pearls": {"known": 12, "unknown": 0},
            "zees": [{"name": "French Exclusive Economic Zone", "gold": True, "poe": ["La Pallice"], "mrgid": 5677}],
            "flags": [],
            "ampCount": 1,
            "alertCount": 0,
        }],
        "pearlsWarmed": 12,
        "pearlsUnknown": 0,
        "comment": {"text": "", "source": "rules", "cached": True},
    }
    ici_bag = preparing_ici(46.15, -1.16)
    ici_bag["status"] = STATUS_READY
    ici_bag["zee"] = {"name": "France", "mrgid": 5677}
    return {
        "moments": {
            "status": STATUS_READY,
            "voyageId": DEFAULT_ROUTE,
            "moments": moments,
            "count": len(moments),
            "journal": {
                "days": [{"day": "2026-05-15", "count": 2}],
                "count": 2,
                "first": "2026-05-15",
                "last": "2026-05-15",
                "latest": moments,
                "events": moments,
                "kinds": ["stop"],
            },
        },
        "film": {
            "status": STATUS_READY,
            "films": {
                "fr:150": film_fr,
                "fr:0": film_fr,
                "fr:180": film_fr,
                "en:150": film_en,
                "en:0": film_en,
                "en:180": film_en,
            },
        },
        "eta": {
            "status": STATUS_READY,
            "stops": {
                "Nouméa": eta_row,
                "Fort-de-France (Martinique)": eta_row,
                "Dzaoudzi (Mayotte)": eta_row,
                "Papeete (Polynésie française)": eta_row,
                "La Rochelle": eta_row,
                "Ajaccio (Corse)": eta_row,
                "Saint-Maur (Berry, Indre)": eta_row,
            },
        },
        "climo": {
            "status": STATUS_READY,
            "clock": clock,
            "fiches": [
                {"lat": 46.15, "lon": -1.16, "iso": "2026-05-15T12:00:00Z", "regime": "climatology"},
                {"lat": -22.27, "lon": 166.44, "iso": "2026-09-17T08:00:00Z", "regime": "climatology"},
            ],
        },
        "ici": {"status": STATUS_READY, "bags": [
            {"lat": 46.8075, "lon": 1.6358, "bag": {**preparing_ici(46.8075, 1.6358), "status": STATUS_READY}},
            {"lat": 46.15, "lon": -1.16, "bag": ici_bag},
        ]},
        "plan_review": review,
    }


def seed_disk(dest: Optional[Path] = None) -> dict[str, str]:
    """Remplit (ou recopie) le stock disque avant d'ouvrir le navigateur."""
    root = Path(dest) if dest else default_disk_dir()
    store = configure(disk_dir=root, mongo_url="")
    key = current_key()
    wrote = {}
    for family, payload in seed_payloads().items():
        store.put(family, payload, key=key)
        wrote[family] = "seeded"
    log.info("stock officiel disque semé dans %s (%s)", root, key)
    return wrote


def _mark_filled(family: str) -> None:
    _FILL_GEN[family] = _FILL_GEN.get(family, 0) + 1


def _fill_moments() -> Optional[dict]:
    from moment_journal import read_moments, warm_moments  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    import voyage_journal as journal  # noqa: PLC0415

    warm_moments(OFFICIAL_VOYAGE_ID)
    rows = read_moments(OFFICIAL_VOYAGE_ID)
    try:
        snapshot = journal.summary(500)
    except Exception:
        snapshot = None
    _mark_filled("moments")
    return {
        "status": STATUS_READY,
        "voyageId": OFFICIAL_VOYAGE_ID,
        "moments": rows,
        "count": len(rows),
        "journal": snapshot,
    }


def _fill_film() -> Optional[dict]:
    import asyncio  # noqa: PLC0415
    from film_script import official_film  # noqa: PLC0415

    films: dict[str, Any] = {}

    async def _all() -> None:
        for lang in ("fr", "en"):
            for seconds in (0, 150, 180):
                films[f"{lang}:{seconds}"] = await official_film(
                    lang=lang, seconds=seconds, style="raw",
                )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_all())
    else:
        return None
    _mark_filled("film")
    return {"status": STATUS_READY, "films": films}


def _fill_eta() -> Optional[dict]:
    from ensemble_eta import peek_official_eta, preheat_official_eta, tighten_eta_payload  # noqa: PLC0415
    from voyage_api import _now as voy_now, _polar_raw  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    if not voy:
        return None
    when = voy_now()
    stops: dict[str, Any] = {}
    names = [m.get("name") for m in (voy.get("marks") or []) if m.get("name")]
    if not names:
        names = ["Nouméa"]
    polar = _polar_raw(voy.get("expedition_id") or "")
    for name in names:
        try:
            preheat_official_eta(voy, when, polar_raw=polar, stop=name)
        except Exception as exc:
            log.warning("ETA fond %s: %s", name, exc)
        try:
            stops[name] = tighten_eta_payload(peek_official_eta(voy, name, when), when)
        except Exception as exc:
            log.warning("ETA lecture %s: %s", name, exc)
    _mark_filled("eta")
    return {"status": STATUS_READY, "stops": stops}


def _fill_climo() -> Optional[dict]:
    from voyage_api import _climo_clock  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    from voyage_store import load_voyage, save_voyage  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    if not voy:
        return None
    clock = _climo_clock(voy)
    voy["clock"] = clock
    save_voyage(voy)
    verts = clock.get("vertices") or []
    step = max(1, len(verts) // 80) if verts else 1
    fiches = []
    for v in verts[::step]:
        if v.get("lat") is None:
            continue
        fiches.append({
            "lat": v.get("lat"),
            "lon": v.get("lon"),
            "iso": v.get("iso"),
            "regime": v.get("regime") or v.get("kind") or "climatology",
        })
    _mark_filled("climo")
    return {"status": STATUS_READY, "clock": clock, "fiches": fiches}


def _fill_ici() -> Optional[dict]:
    import asyncio  # noqa: PLC0415
    from ici_engine import ICI_RADIUS_NM, fill_dossier  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    pts = (voy or {}).get("points") or []
    if not pts:
        return {"status": STATUS_READY, "bags": []}
    step = max(1, len(pts) // 24)
    sample = pts[::step][:24]

    async def _one(p: dict) -> Optional[dict]:
        try:
            bag = await fill_dossier(float(p["lat"]), float(p["lon"]), ICI_RADIUS_NM, thin=True)
            return {"lat": p["lat"], "lon": p["lon"], "bag": bag}
        except Exception as exc:
            log.debug("ici fond: %s", exc)
            return None

    async def _all() -> list:
        out = []
        for p in sample:
            row = await _one(p)
            if row:
                out.append(row)
        return out

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        bags = asyncio.run(_all())
    else:
        return None
    _mark_filled("ici")
    return {"status": STATUS_READY, "bags": bags}


def _fill_plan_review() -> Optional[dict]:
    from plan_review import comment_plan, review_official  # noqa: PLC0415
    from voyage_api import _now as voy_now, _run_async  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    if not voy:
        return None
    out = review_official(voy, voy_now(), season=False)
    try:
        from plan_alerts import evaluate_plan  # noqa: PLC0415

        ev = evaluate_plan(voy, now=voy_now())
        counts: dict[Any, int] = {}
        for lg in ev.get("legs") or []:
            n = len(lg.get("alerts") or [])
            if lg.get("idx") is not None:
                counts[int(lg["idx"])] = n
            counts[(lg.get("from"), lg.get("to"))] = n
        for i, row in enumerate(out.get("legs") or []):
            n = counts.get(i)
            if n is None:
                n = counts.get((row.get("from"), row.get("to")))
            if n is not None:
                row["alertCount"] = int(n)
    except Exception as exc:
        log.debug("alertCount fond: %s", exc)
    try:
        out["comment"] = _run_async(comment_plan(out.get("legs") or []))
    except Exception:
        out["comment"] = {"text": "", "source": "rules", "cached": False}
    out["status"] = STATUS_READY
    _mark_filled("plan_review")
    return out


FILLERS: dict[str, Callable[[], Optional[dict]]] = {
    "moments": _fill_moments,
    "film": _fill_film,
    "eta": _fill_eta,
    "climo": _fill_climo,
    "ici": _fill_ici,
    "plan_review": _fill_plan_review,
}


def fill_family(family: str, *, force: bool = False) -> str:
    if family not in FAMILIES:
        raise ValueError(family)
    store = get_store()
    key = current_key()
    if not force and store.get(family, key=key):
        return "kept"
    fn = FILLERS[family]
    payload = fn()
    if payload is None:
        return "empty"
    store.put(family, payload, key=key)
    return "wrote"


def fill_missing(*, force: bool = False, fillers: Optional[dict] = None) -> dict[str, str]:
    """Calcule ce qui manque ou a vieilli. Hors chemin HTTP."""
    used = fillers or FILLERS
    store = get_store()
    key = current_key()
    done: dict[str, str] = {}
    for family in FAMILIES:
        if not force and store.get(family, key=key):
            done[family] = "kept"
            continue
        fn = used.get(family)
        if fn is None:
            done[family] = "skip"
            continue
        try:
            payload = fn()
        except Exception as exc:
            log.warning("fond %s: %s", family, exc)
            done[family] = "error"
            continue
        if payload is None:
            done[family] = "empty"
            continue
        store.put(family, payload, key=key)
        done[family] = "wrote"
    return done


def _worker_loop() -> None:
    while True:
        try:
            from voyage_api import seed_official_voyage  # noqa: PLC0415

            seed_official_voyage()
        except Exception as exc:
            log.debug("semis fond: %s", exc)
        try:
            fill_missing()
        except Exception as exc:
            log.warning("travail de fond: %s", exc)
        time.sleep(WORKER_PERIOD_S)


def _worker_enabled() -> bool:
    raw = (os.getenv("NAVIGUIDE_OFFICIAL_WORKER") or "1").strip().lower()
    if raw in ("0", "false", "no"):
        return False
    if os.getenv("PYTEST_CURRENT_TEST") and raw != "force":
        return False
    return True


def start_worker() -> bool:
    """Au boot : fil daemon. Jamais bloquant."""
    global _WORKER_STARTED
    if not _worker_enabled():
        return False
    with _LOCK:
        if _WORKER_STARTED:
            return False
        _WORKER_STARTED = True
    threading.Thread(target=_worker_loop, name="naviguide-official-store", daemon=True).start()
    return True


def nudge() -> None:
    """Réveille un passage (non bloquant). Le client n'attend jamais."""
    if not _worker_enabled():
        return
    threading.Thread(target=lambda: fill_missing(), name="naviguide-official-nudge", daemon=True).start()


def materialize_clock() -> Optional[dict]:
    """Tests : pose l'horloge dans le voyage ET le stock (hors HTTP)."""
    clock_payload = _fill_climo()
    if not clock_payload:
        return None
    get_store().put("climo", clock_payload)
    return clock_payload.get("clock")


if __name__ == "__main__":
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "seed").strip()
    if cmd == "seed":
        print(json.dumps(seed_disk(), ensure_ascii=False))
    else:
        raise SystemExit(f"commande inconnue: {cmd}")
