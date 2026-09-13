#!/usr/bin/env python3
"""WAVERYS PT3H → hs_p50 / hs_p90 pour un mois calendaire, toutes années.

Un mois à la fois, une année à la fois, pas de temps par pas de temps.
Jamais le cube mondial en RAM. Les percentiles viennent d'un histogramme
Hs (pas d'une moyenne P1M étiquetée P90).

Reprise : relancer la même commande reprend à l'année suivante
(``wave-MM.partial.npz``).

À lancer sur le Mac (ou une grosse machine), **pas** sur le VPS 8 Go.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cmems_auth import login, open_dataset

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend" / "data" / "climatology" / "wave"
PRODUCT = "GLOBAL_MULTIYEAR_WAV_001_032"
DATASET = "cmems_mod_glo_wav_my_0.2deg_PT3H-i"
PERIOD = "1993-2019"
DOI = "10.48670/moi-00022"
NATIVE_DEG = 0.2

# Hs 0–20 m par pas de 5 cm ; Tm02 0–20 s par pas de 0,1 s.
HS_BIN = 0.05
HS_BINS = 400
PER_BIN = 0.1
PER_BINS = 200
MIN_SAMPLES = 20
TIME_CHUNK = 16
ACC_KEYS = (
    "lats", "lons", "count", "hs_hist", "per_hist", "sin_sum", "cos_sum",
)


def hist_percentiles(counts, qs, bin_width):
    """Percentiles depuis un histogramme (ny, nx, nbins). NaN si compteur 0."""
    import numpy as np

    total = counts.sum(axis=-1)
    cdf = np.cumsum(counts, axis=-1)
    out = []
    safe_total = np.maximum(total, 1)
    for q in qs:
        target = (float(q) / 100.0) * safe_total
        ge = cdf >= target[..., None]
        idx = ge.argmax(axis=-1)
        prev = np.where(
            idx > 0,
            np.take_along_axis(cdf, np.maximum(idx - 1, 0)[..., None], -1)[..., 0],
            0,
        )
        in_bin = np.maximum(
            np.take_along_axis(counts, idx[..., None], -1)[..., 0],
            1,
        )
        frac = np.clip((target - prev) / in_bin, 0.0, 1.0)
        val = (idx.astype("float64") + frac) * float(bin_width)
        val = np.where(total > 0, val, np.nan)
        out.append(val.astype("float32"))
    return out


def _month_range(month: int, year: int) -> tuple[str, str]:
    start = f"{year}-{month:02d}-01T00:00:00"
    if month == 12:
        end = f"{year + 1}-01-01T00:00:00"
    else:
        end = f"{year}-{month + 1:02d}-01T00:00:00"
    return start, end


def _is_out_of_bounds(exc: BaseException) -> bool:
    name = type(exc).__name__
    return "OutOfDatasetBounds" in name or "out of bounds" in str(exc).lower()


def _dim_names(ds) -> tuple[str, str, str]:
    lat_name = "latitude" if "latitude" in ds.dims or "latitude" in ds.coords else "lat"
    lon_name = "longitude" if "longitude" in ds.dims or "longitude" in ds.coords else "lon"
    time_name = "time" if "time" in ds.dims else "valid_time"
    return lat_name, lon_name, time_name


def _lon_180(ds, lon_name: str):
    import numpy as np

    lon = np.asarray(ds[lon_name].values)
    if lon.size == 0 or float(np.nanmax(lon)) <= 180.0:
        return ds
    lon_new = ((lon + 180.0) % 360.0) - 180.0
    return ds.assign_coords({lon_name: lon_new}).sortby(lon_name)


def _existing_grid(out: Path, month: int):
    dest = out / f"wave-{month:02d}.npz"
    if not dest.is_file():
        return None, None
    try:
        import numpy as np

        data = np.load(dest, allow_pickle=False)
        return data["lats"], data["lons"]
    except Exception:
        return None, None


def _open_year(
    month: int,
    year: int,
    spacing: float,
    target_lats=None,
    target_lons=None,
):
    start, end = _month_range(month, year)
    last_err = None
    for attempt in range(1, 5):
        try:
            ds = open_dataset(
                dataset_id=DATASET,
                variables=["VHM0", "VTM02", "VMDR"],
                start_datetime=start,
                end_datetime=end,
            )
            lat_name, lon_name, time_name = _dim_names(ds)
            ds = _lon_180(ds, lon_name)
            if target_lats is not None and target_lons is not None:
                ds = ds.sel(
                    {lat_name: target_lats, lon_name: target_lons},
                    method="nearest",
                )
            elif spacing > NATIVE_DEG:
                step = max(1, int(round(spacing / NATIVE_DEG)))
                ds = ds.isel({
                    lat_name: slice(None, None, step),
                    lon_name: slice(None, None, step),
                })
            return ds, lat_name, lon_name, time_name
        except Exception as exc:
            if _is_out_of_bounds(exc):
                print(f"  skip {year}-{month:02d} hors archive", file=sys.stderr)
                return None
            last_err = exc
            wait = 4 * (2 ** (attempt - 1))
            print(f"  retry {attempt}/4 dans {wait}s ({type(exc).__name__})", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"échec subset {year}-{month:02d}") from last_err


def _new_acc(lats, lons):
    import numpy as np

    ny, nx = len(lats), len(lons)
    return {
        "lats": lats.astype("float32"),
        "lons": lons.astype("float32"),
        "count": np.zeros((ny, nx), dtype="int32"),
        "hs_hist": np.zeros((ny, nx, HS_BINS), dtype="uint16"),
        "per_hist": np.zeros((ny, nx, PER_BINS), dtype="uint16"),
        "sin_sum": np.zeros((ny, nx), dtype="float64"),
        "cos_sum": np.zeros((ny, nx), dtype="float64"),
    }


def _save_partial(path: Path, acc: dict, year_next: int) -> None:
    import numpy as np

    np.savez(path, year_next=np.int32(year_next), **acc)


def _load_partial(path: Path) -> tuple[dict, int] | None:
    import numpy as np

    if not path.is_file():
        return None
    try:
        data = np.load(path, allow_pickle=False)
        year_next = int(data["year_next"])
        acc = {k: data[k].copy() for k in ACC_KEYS}
    except Exception:
        return None
    return acc, year_next


def _bin_index(values, bin_width: float, n_bins: int):
    import numpy as np

    idx = np.floor(values / bin_width).astype("int32")
    return np.clip(idx, 0, n_bins - 1)


def accumulate(acc: dict, hs, period=None, direction=None) -> None:
    """Ajoute un cube (time, lat, lon) aux histogrammes. Pas de concat globale."""
    import numpy as np

    if hs.ndim == 2:
        hs = hs[None, ...]
        period = None if period is None else period[None, ...]
        direction = None if direction is None else direction[None, ...]
    for t in range(hs.shape[0]):
        h = np.asarray(hs[t], dtype="float32")
        ok = np.isfinite(h)
        if not ok.any():
            continue
        acc["count"] += ok.astype("int32")
        hi = _bin_index(np.where(ok, h, 0.0), HS_BIN, HS_BINS)
        ii, jj = np.nonzero(ok)
        acc["hs_hist"][ii, jj, hi[ii, jj]] += np.uint16(1)
        if period is not None:
            p = np.asarray(period[t], dtype="float32")
            pok = ok & np.isfinite(p)
            if pok.any():
                pi = _bin_index(np.where(pok, p, 0.0), PER_BIN, PER_BINS)
                pii, pjj = np.nonzero(pok)
                acc["per_hist"][pii, pjj, pi[pii, pjj]] += np.uint16(1)
        if direction is not None:
            d = np.asarray(direction[t], dtype="float32")
            dok = ok & np.isfinite(d)
            if dok.any():
                rad = np.radians(np.where(dok, d, np.nan))
                acc["sin_sum"] += np.nansum(np.sin(rad)[None, ...], axis=0)
                acc["cos_sum"] += np.nansum(np.cos(rad)[None, ...], axis=0)


def finalize(acc: dict, min_samples: int = MIN_SAMPLES) -> dict:
    import numpy as np

    p50, p90 = hist_percentiles(acc["hs_hist"], (50, 90), HS_BIN)
    per, = hist_percentiles(acc["per_hist"], (50,), PER_BIN)
    dirm = (np.degrees(np.arctan2(acc["sin_sum"], acc["cos_sum"])) + 360.0) % 360.0
    sea = acc["count"] >= int(min_samples)
    p90 = np.maximum(p90, p50)
    nan = ~sea
    p50 = p50.copy()
    p90 = p90.copy()
    per = per.copy()
    dirm = dirm.astype("float32")
    p50[nan] = np.nan
    p90[nan] = np.nan
    per[nan] = np.nan
    dirm[nan] = np.nan
    return {
        "lats": acc["lats"],
        "lons": acc["lons"],
        "hs_p50": p50,
        "hs_p90": p90,
        "period": per,
        "dir": dirm,
        "sea_mask": sea,
        "sample_count": acc["count"],
    }


def _sidecar_is_complete_pct(path: Path, year_start: int, year_end: int) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if data.get("stat") != "p50_p90":
        return False
    return data.get("years") == f"{year_start}-{year_end}"


def generate_month(
    month: int,
    year_start: int,
    year_end: int,
    spacing: float,
    out: Path,
    time_chunk: int = TIME_CHUNK,
    min_samples: int = MIN_SAMPLES,
) -> Path:
    import numpy as np

    dest = out / f"wave-{month:02d}.npz"
    sidecar = out / f"wave-{month:02d}.json"
    partial = out / f"wave-{month:02d}.partial.npz"
    years = list(range(year_start, year_end + 1))
    loaded = _load_partial(partial)
    exist_lats, exist_lons = _existing_grid(out, month)
    if loaded:
        acc, year_next = loaded
        todo = [y for y in years if y >= year_next]
        print(f"reprise mois {month:02d} à l'année {year_next}", file=sys.stderr)
    else:
        acc = None
        todo = years

    t0 = time.time()
    for i, year in enumerate(todo, start=1):
        print(f"mois {month:02d}  année {year}  ({i}/{len(todo)})  {DATASET}", file=sys.stderr)
        opened = _open_year(
            month, year, spacing,
            target_lats=None if acc is None else acc["lats"],
            target_lons=None if acc is None else acc["lons"],
        )
        if opened is None:
            if acc is not None:
                _save_partial(partial, acc, year + 1)
            continue
        ds, lat_name, lon_name, time_name = opened
        if acc is None and exist_lats is not None and exist_lons is not None:
            # Première année : coller la maille V0 mean si elle est déjà là.
            if abs(float(exist_lats[1] - exist_lats[0]) - spacing) < 0.05:
                ds = ds.sel(
                    {lat_name: exist_lats, lon_name: exist_lons},
                    method="nearest",
                )
        n_time = int(ds.sizes.get(time_name, 1))
        lats = ds[lat_name].values.astype("float32")
        lons = ds[lon_name].values.astype("float32")
        if acc is None:
            acc = _new_acc(lats, lons)
        for t0i in range(0, n_time, time_chunk):
            sl = ds.isel({time_name: slice(t0i, t0i + time_chunk)})
            hs = np.asarray(sl["VHM0"].values, dtype="float32")
            period = np.asarray(sl["VTM02"].values, dtype="float32")
            direction = np.asarray(sl["VMDR"].values, dtype="float32")
            accumulate(acc, hs, period, direction)
            del sl, hs, period, direction
            gc.collect()
        del ds
        gc.collect()
        _save_partial(partial, acc, year + 1)

    if acc is None:
        raise SystemExit(f"aucune année téléchargée pour le mois {month}")

    fields = finalize(acc, min_samples=min_samples)
    tmp = dest.with_name(dest.stem + ".tmp.npz")
    np.savez_compressed(
        tmp,
        lats=fields["lats"],
        lons=fields["lons"],
        hs_p50=fields["hs_p50"],
        hs_p90=fields["hs_p90"],
        period=fields["period"],
        dir=fields["dir"],
        sea_mask=fields["sea_mask"],
        sample_count=fields["sample_count"],
        stat=np.array(["p50_p90"]),
    )
    tmp.replace(dest)
    sidecar.write_text(json.dumps({
        "kind": "climatology",
        "month": month,
        "period": PERIOD,
        "source_ids": [PRODUCT],
        "doi": DOI,
        "dataset": DATASET,
        "stat": "p50_p90",
        "note": (
            "Hs P50/P90 from PT3H histograms (0.05 m bins). "
            "Not a P1M mean. Direction is circular mean of VMDR."
        ),
        "grid_spacing_deg": spacing,
        "years": f"{year_start}-{year_end}",
        "hs_bin_m": HS_BIN,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=2) + "\n", encoding="utf-8")
    if partial.is_file():
        partial.unlink()
    elapsed = int(time.time() - t0)
    print(f"wrote {dest} stat=p50_p90  {elapsed}s")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Hs P50/P90 WAVERYS PT3H — un mois ou les 12. Pas sur le VPS."
    )
    ap.add_argument("--month", type=int, default=None, help="1–12 ; omit avec --all")
    ap.add_argument("--all", action="store_true", help="les 12 mois, dans l'ordre")
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="saute un mois déjà en p50_p90 (pas une moyenne P1M)",
    )
    ap.add_argument("--year-start", type=int, default=1993)
    ap.add_argument("--year-end", type=int, default=2019)
    ap.add_argument("--spacing", type=float, default=0.4, help="maille stockée (°)")
    ap.add_argument("--time-chunk", type=int, default=TIME_CHUNK)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    if args.all:
        months = list(range(1, 13))
    elif args.month is not None:
        if args.month < 1 or args.month > 12:
            raise SystemExit("month 1–12")
        months = [args.month]
    else:
        raise SystemExit("indique --month N ou --all")

    try:
        import numpy as np  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Prérequis : pip install copernicusmarine xarray netCDF4 numpy python-dotenv"
        ) from exc

    args.out.mkdir(parents=True, exist_ok=True)
    print("login Copernicus…", file=sys.stderr)
    login()
    for month in months:
        sidecar = args.out / f"wave-{month:02d}.json"
        if args.skip_existing and _sidecar_is_complete_pct(
            sidecar, args.year_start, args.year_end,
        ):
            print(
                f"mois {month:02d} déjà en p50_p90 {args.year_start}-{args.year_end} — skip",
                file=sys.stderr,
            )
            continue
        generate_month(
            month,
            args.year_start,
            args.year_end,
            args.spacing,
            args.out,
            time_chunk=max(1, int(args.time_chunk)),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
