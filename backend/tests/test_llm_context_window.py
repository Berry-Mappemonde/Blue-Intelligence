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
