"""Le chargement du Mongo de CI ne peut pas viser Atlas ni le VPS."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seed_ci_mongo.py"
_spec = importlib.util.spec_from_file_location("seed_ci_mongo", _SCRIPT)
seed_ci = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["seed_ci_mongo"] = seed_ci
_spec.loader.exec_module(seed_ci)


def test_accepts_loopback_ci_database():
    seed_ci.assert_ci_target("mongodb://127.0.0.1:27017", "bi_ci")
    seed_ci.assert_ci_target("mongodb://localhost:27017/bi_ci", "bi_ci")


@pytest.mark.parametrize("url", [
    "mongodb+srv://u:p@cluster.mongodb.net/app",
    "mongodb://user:pw@127.0.0.1:27017",
    "mongodb://135.125.226.16:27017",
    "mongodb://vps.ovh.net:27017",
    "mongodb://nebius.example:27017",
    "http://127.0.0.1:27017",
    "",
])
def test_refuses_non_ci_targets(url):
    with pytest.raises(SystemExit):
        seed_ci.assert_ci_target(url, "bi_ci")


def test_refuses_any_other_database_name():
    with pytest.raises(SystemExit):
        seed_ci.assert_ci_target("mongodb://127.0.0.1:27017", "blue_intelligence")
