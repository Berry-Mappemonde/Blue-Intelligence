"""LLM readers send the window the caller chose: 20,000 chars by default, 40,000 on the catalog path."""
import asyncio

import pytest

from app.core import claude, llm, nvidia
from app.services import poe_pipeline as poe

ZONE = {"name": "Bermuda", "sovereign": "United Kingdom", "mrgid": 8402}
CONTEXT = "x" * 30000 + " TAILMARK"


def _with_window(chars, coro_fn):
    async def run():
        token = llm.llm_context_chars.set(chars)
        try:
            return await coro_fn()
        finally:
            llm.llm_context_chars.reset(token)
    return asyncio.run(run())


def _nightshift_spy(monkeypatch):
    prompts = []

    async def fake(prompt, system, *, json_mode, role, log=None):
        prompts.append(prompt)
        return {"parsed": {"ports": []}, "model": "nemotron-test"}

    monkeypatch.setattr(llm, "_nightshift", fake)
    return prompts


def test_default_window_stays_20000(monkeypatch):
    prompts, logs = _nightshift_spy(monkeypatch), []
    asyncio.run(llm.extract_ports_nightshift(CONTEXT, ZONE, log=logs.append))
    assert "x" * 20000 in prompts[0] and "x" * 20001 not in prompts[0]
    assert "TAILMARK" not in prompts[0]
    assert logs[-1].endswith("sur 20000 chars envoyés")


def test_widened_window_sends_the_whole_catalog_context(monkeypatch):
    prompts, logs = _nightshift_spy(monkeypatch), []
    _with_window(40000, lambda: llm.extract_ports_nightshift(CONTEXT, ZONE, log=logs.append))
    assert "TAILMARK" in prompts[0]
    assert logs[-1].endswith(f"sur {len(CONTEXT)} chars envoyés")


def test_every_reader_honours_the_window(monkeypatch):
    seen = {}

    async def fake_openrouter(prompt, system, settings, max_tokens, images=None):
        seen["openrouter"] = prompt
        return {"ports": []}

    async def fake_nim(system, prompt, settings, **kwargs):
        seen["nvidia"] = prompt
        return {"ports": []}, "nvidia/test-model"

    monkeypatch.setattr(llm, "_json_openrouter", fake_openrouter)
    monkeypatch.setattr(nvidia, "complete_json_nvidia_tracked", fake_nim)

    async def readers():
        await llm.extract_ports_openrouter(CONTEXT, ZONE, settings={})
        await nvidia.extract_ports_nvidia(CONTEXT, ZONE, settings={})
        seen["claude"] = claude.build_extract_payload(ZONE, CONTEXT)["messages"][0]["content"][0]["text"]

    asyncio.run(readers())
    assert not any("TAILMARK" in p for p in seen.values())
    _with_window(40000, readers)
    assert all("TAILMARK" in p for p in seen.values()), seen.keys()


def test_window_reaches_the_parallel_readers(monkeypatch):
    sent = []

    async def fake_extract(context, zone, settings=None, log=None):
        sent.append(len(llm.reader_context(context)))
        return [{"name": "St. George's", "city": None, "note": None}]

    import app.core.ml as ml
    monkeypatch.setattr(poe, "extract_ports", fake_extract)
    monkeypatch.setattr(ml, "extract_entities", lambda text: [])
    _with_window(40000, lambda: poe._extract_ports_core(CONTEXT, ZONE, lambda m: None))
    asyncio.run(poe._extract_ports_core(CONTEXT, ZONE, lambda m: None))
    assert sent == [len(CONTEXT), 20000]
    assert llm.llm_context_chars.get() == llm.LLM_CONTEXT_CHARS


@pytest.mark.parametrize("raw, catalog, branch, window, chars", [
    ("Port list. " * 6000, [{"name": "Hamilton"}], "catalog", 40000, 40000),
    ("short official page about customs", [], "raw", 20000, 33),
])
def test_extraction_context_branches(raw, catalog, branch, window, chars):
    context, got_window, got_branch = poe.extraction_context(raw, catalog, "ports of entry")
    assert (got_branch, got_window, len(context)) == (branch, window, chars)


def test_long_prose_is_condensed_to_the_default_window(monkeypatch):
    monkeypatch.setattr(poe, "looks_like_port_catalog", lambda raw: False)
    raw = "\n\n".join(f"Paragraph {i} about customs formalities and visas." for i in range(1500))
    context, window, branch = poe.extraction_context(raw, [], "ports of entry")
    assert branch == "rag" and window == llm.LLM_CONTEXT_CHARS
    assert len(context) <= llm.LLM_CONTEXT_CHARS < len(raw)


# --- generate_zone_poe: per-zone window and the 0-port retry -------------------------

class _Zones:
    def __init__(self, zones):
        self.zones = zones

    async def find_one(self, query):
        return dict(self.zones[query["mrgid"]])

    async def update_one(self, *args, **kwargs):
        return None


class _DB:
    def __init__(self, zones):
        self.eez_zones = _Zones(zones)


def _stub_zone_pipeline(monkeypatch, texts, extract, synthesis=None):
    """Stub search, collection and persistence around the real context and window steps."""
    import app.db

    async def no_settings():
        return {}

    async def find_sources(zone, *args, **kwargs):
        return [{"url": f"https://gov.example/{zone['mrgid']}", "official": True}], True, None

    async def collect(official, log, rec=None, **kwargs):
        return [texts[int(official[0]["url"].rsplit("/", 1)[1])]], {}, official, {}

    async def grounded(zone, whitelist, log, query_override=None):
        return None, synthesis

    async def persist(db, zone, docs, status, *args, **kwargs):
        return {"mrgid": zone["mrgid"], "status": status, "poe_count": len(docs)}

    monkeypatch.setattr(app.db, "get_settings", no_settings)
    monkeypatch.setattr(poe, "load_exceptions", lambda: {})
    monkeypatch.setattr(poe, "build_whitelist", lambda *a, **k: [])
    monkeypatch.setattr(poe, "_find_sources", find_sources)
    monkeypatch.setattr(poe, "_collect_texts", collect)
    monkeypatch.setattr(poe, "search_grounded", grounded)
    monkeypatch.setattr(poe, "extract_structured_ports",
                        lambda raw: [{"name": "Catalog Port"}] if "CATALOG" in raw else [])
    monkeypatch.setattr(poe, "looks_like_port_catalog", lambda raw: "CATALOG" in raw)
    monkeypatch.setattr(poe, "remember_seed_urls", lambda *a, **k: [])
    monkeypatch.setattr(poe, "_extract_and_geocode", extract)
    monkeypatch.setattr(poe, "_persist_zone", persist)


def test_concurrent_zones_each_read_with_their_own_window(monkeypatch):
    catalog_text = "CATALOG " + "x" * 30000 + " TAIL1"
    prose = "\n\n".join(f"Paragraph {i} about customs formalities and visas." for i in range(700))
    zones = {1: {"mrgid": 1, "name": "Catalogland"}, 2: {"mrgid": 2, "name": "Proseland"}}
    prompts, seen, arrived, done = _nightshift_spy(monkeypatch), {}, [], []

    async def run():
        both_set, both_read = asyncio.Event(), asyncio.Event()

        async def extract(zone, context, used_sources, log, rec=None, run=None,
                          catalog_text=None, settings=None):
            # Both zones set their window before either reader runs, and neither
            # finishes (and resets it) before both have read.
            arrived.append(zone["mrgid"])
            if len(arrived) == 2:
                both_set.set()
            await both_set.wait()
            await llm.extract_ports_nightshift(context, zone)
            seen[zone["mrgid"]] = (llm.llm_context_chars.get(), len(llm.reader_context(context)))
            done.append(zone["mrgid"])
            if len(done) == 2:
                both_read.set()
            await both_read.wait()
            return []

        _stub_zone_pipeline(monkeypatch, {1: catalog_text, 2: prose}, extract)
        db = _DB(zones)
        await asyncio.gather(poe.generate_zone_poe(db, 1), poe.generate_zone_poe(db, 2))
        return llm.llm_context_chars.get()

    outer = asyncio.run(run())
    assert seen[1] == (poe.CATALOG_CONTEXT_CHARS, len(catalog_text))
    assert seen[2][0] == llm.LLM_CONTEXT_CHARS and seen[2][1] <= llm.LLM_CONTEXT_CHARS < len(prose)
    assert sum("TAIL1" in p for p in prompts) == 1
    assert outer == llm.LLM_CONTEXT_CHARS


def test_zero_port_retry_puts_the_synthesis_where_readers_see_it(monkeypatch):
    catalog_text = "CATALOG " + "x" * 45000
    calls = []

    async def extract(zone, context, used_sources, log, rec=None, run=None,
                      catalog_text=None, settings=None):
        calls.append(llm.reader_context(context))
        return []

    _stub_zone_pipeline(monkeypatch, {1: catalog_text}, extract,
                        synthesis="SYNTH-MARKER Hamilton is the port of entry.")
    result = asyncio.run(poe.generate_zone_poe(_DB({1: {"mrgid": 1, "name": "Catalogland"}}), 1))
    assert len(calls) == 2 and result["status"] == "erreur"
    assert "SYNTH-MARKER" not in calls[0]
    assert calls[1].startswith("[SYNTHÈSE DE RECHERCHE (à recouper)]\nSYNTH-MARKER")
    assert len(calls[1]) == poe.CATALOG_CONTEXT_CHARS
