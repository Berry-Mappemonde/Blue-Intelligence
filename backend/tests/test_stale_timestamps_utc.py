"""Horodatages « …Z » : lus en UTC, jamais en heure locale.

`generated_at` / `checked_at` / `enriched_at` sont écrits en UTC
(`time.strftime(…, time.gmtime())`). Les trois lecteurs utilisaient
`time.mktime`, qui interprète la structure comme une heure *locale* : la
fenêtre « périmé » glissait alors du fuseau de la machine (±14 h), un doc
pouvait être déclaré périmé le jour même de sa génération (fuseau est), et
le cycle de rafraîchissement automatique repoussait une zone fraîche
(fuseau ouest).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.marina_enrich import is_stale as marina_is_stale  # noqa: E402
from app.services.poe_pipeline import is_stale as poe_is_stale  # noqa: E402
from app.routers.formalities import _ts_of  # noqa: E402


class _Tz:
    """Run the body under another TZ (Unix: time.tzset)."""

    def __init__(self, tz: str):
        self.tz = tz
        self.prev = None

    def __enter__(self):
        self.prev = os.environ.get("TZ")
        os.environ["TZ"] = self.tz
        time.tzset()
        return self

    def __exit__(self, *exc):
        if self.prev is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self.prev
        time.tzset()


UTC_MIDNIGHT = "2026-06-15T00:00:00Z"
UTC_MIDNIGHT_EPOCH = 1781481600.0  # 2026-06-15T00:00:00Z


def test_ts_of_reads_the_z_timestamp_as_utc_in_any_timezone():
    for tz in ("UTC", "Asia/Kolkata", "America/Los_Angeles", "Pacific/Kiritimati"):
        with _Tz(tz):
            assert _ts_of(UTC_MIDNIGHT) == UTC_MIDNIGHT_EPOCH, tz


def test_poe_is_stale_ignores_the_machine_timezone():
    fresh = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    old = {"generated_at": "2020-01-01T00:00:00Z"}
    for tz in ("UTC", "Asia/Kolkata", "America/Los_Angeles"):
        with _Tz(tz):
            assert poe_is_stale(fresh) is False, tz
            assert poe_is_stale(old) is True, tz


def test_poe_is_stale_boundary_is_the_utc_instant():
    """Juste avant / juste après STALE_DAYS, en UTC comme en heure locale."""
    from app.services.poe_pipeline import STALE_DAYS

    now = time.time()
    inside = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - (STALE_DAYS - 1) * 86400))
    outside = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - (STALE_DAYS + 1) * 86400))
    for tz in ("UTC", "Asia/Kolkata"):
        with _Tz(tz):
            assert poe_is_stale({"generated_at": inside}) is False, tz
            assert poe_is_stale({"generated_at": outside}) is True, tz


def test_marina_is_stale_ignores_the_machine_timezone():
    fresh = {"enriched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    old = {"enriched_at": "2020-01-01T00:00:00Z"}
    for tz in ("UTC", "Asia/Kolkata", "America/Los_Angeles"):
        with _Tz(tz):
            assert marina_is_stale(fresh) is False, tz
            assert marina_is_stale(old) is True, tz


def test_marina_is_stale_default_window_is_365_days():
    now = time.time()
    inside = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 364 * 86400))
    outside = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 366 * 86400))
    assert marina_is_stale({"enriched_at": inside}) is False
    assert marina_is_stale({"enriched_at": outside}) is True
