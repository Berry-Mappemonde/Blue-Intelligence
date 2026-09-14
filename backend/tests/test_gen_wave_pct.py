"""Hs P50/P90 histograms — no Copernicus, no cube in RAM."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "climatology"))

import gen_wave_pct as g  # noqa: E402


def test_hist_percentiles_match_numpy_on_flat_cell():
    samples = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    counts = np.zeros((1, 1, g.HS_BINS), dtype="uint16")
    for v in samples:
        idx = int(np.floor(v / g.HS_BIN))
        counts[0, 0, idx] += 1
    p50, p90 = g.hist_percentiles(counts, (50, 90), g.HS_BIN)
    assert p90[0, 0] >= p50[0, 0] > 0
    assert abs(float(p50[0, 0]) - 5.0) < 0.15
    assert abs(float(p90[0, 0]) - 9.0) < 0.15


def test_accumulate_finalize_p90_gt_p50_and_sea_mask():
    rng = np.random.default_rng(42)
    hs = rng.gamma(2.0, 1.2, size=(80, 3, 3)).astype("float32")
    hs[:, 2, 2] = np.nan
    period = (hs * 3.0) + 4.0
    direction = np.full_like(hs, 220.0)
    lats = np.array([-40.4, -40.0, -39.6], dtype="float32")
    lons = np.array([9.6, 10.0, 10.4], dtype="float32")
    acc = g._new_acc(lats, lons)
    g.accumulate(acc, hs, period, direction)
    out = g.finalize(acc, min_samples=10)
    assert out["hs_p90"][0, 0] >= out["hs_p50"][0, 0] > 0
    assert bool(out["sea_mask"][0, 0]) is True
    assert bool(out["sea_mask"][2, 2]) is False
    assert np.isnan(out["hs_p50"][2, 2])
    expected = float(np.nanpercentile(hs[:, 0, 0], 50))
    assert abs(float(out["hs_p50"][0, 0]) - expected) < 0.2
    assert 180 < float(out["dir"][0, 0]) < 260


def test_accumulate_two_chunks_equals_one_pass():
    rng = np.random.default_rng(1)
    hs = rng.gamma(2.0, 1.0, size=(40, 2, 2)).astype("float32")
    lats = np.array([0.0, 0.4], dtype="float32")
    lons = np.array([0.0, 0.4], dtype="float32")
    one = g._new_acc(lats, lons)
    g.accumulate(one, hs, hs * 2, np.full_like(hs, 90.0))
    two = g._new_acc(lats, lons)
    g.accumulate(two, hs[:15], hs[:15] * 2, np.full_like(hs[:15], 90.0))
    g.accumulate(two, hs[15:], hs[15:] * 2, np.full_like(hs[15:], 90.0))
    a, b = g.finalize(one), g.finalize(two)
    np.testing.assert_allclose(a["hs_p50"], b["hs_p50"], atol=1e-5)
    np.testing.assert_allclose(a["hs_p90"], b["hs_p90"], atol=1e-5)


def test_sidecar_complete_pct_rejects_mean(tmp_path):
    path = tmp_path / "wave-07.json"
    path.write_text(json.dumps({"stat": "mean", "years": "1993-2019"}), encoding="utf-8")
    assert g._sidecar_is_complete_pct(path, 1993, 2019) is False
    path.write_text(json.dumps({"stat": "p50_p90", "years": "1993-2019"}), encoding="utf-8")
    assert g._sidecar_is_complete_pct(path, 1993, 2019) is True
    assert g._sidecar_is_complete_pct(path, 1993, 2018) is False
