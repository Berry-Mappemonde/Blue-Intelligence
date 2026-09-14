"""Review Formalités : documents, pin mrgid, extract, juge local ∥ LLM."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.nvidia import CHAINS, chat_payload
from app.core.vision_msg import claude_user_content, openai_user_content
from app.services.poe_pipeline import remember_review_pins, seed_url_candidates
from app.services.review_doc_picker import (
    _evidence_for, local_pick, merge_picks, suggest_eez_documents,
)
from app.services.review_extract import extract_gold_ports
from app.services import review_gold, review_queue
from test_review_queue import _db, _prepare_france_gold


def test_openai_and_claude_vision_parts():
    jpeg = b"\xff\xd8\xff" + b"x" * 20
    oa = openai_user_content("hello", [jpeg])
    assert oa[0]["type"] == "text"
    assert oa[1]["type"] == "image_url"
    assert oa[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    cl = claude_user_content("hello", [jpeg])
    assert cl[1]["type"] == "image"
    assert cl[1]["source"]["media_type"] == "image/jpeg"


def test_local_pick_keeps_sufficient_catalog():
    ev = [
        {
            "url": "https://gob.mx/list.pdf",
            "sufficient": True, "looks_catalog": True,
            "catalog_n": 12, "bonus": 0.6,
        },
        {
            "url": "https://gob.mx/news",
            "sufficient": False, "looks_catalog": False,
            "catalog_n": 0, "bonus": 0.0,
        },
    ]
    picked = local_pick(ev)
    assert picked["keep"] == ["https://gob.mx/list.pdf"]
    assert "https://gob.mx/news" in picked["drop"]
    assert picked["engine"] == "local"


def test_merge_picks_prefers_llm_listed_urls():
    local = {
        "keep": ["https://a.example/list.pdf"],
        "drop": ["https://b.example/home"],
        "list_kind": "mixed_designated",
        "comment": "local",
        "reasons": [],
    }
    llm = {
        "keep": ["https://a.example/list.pdf", "https://invented.example/x"],
        "drop": ["https://b.example/home"],
        "list_kind": "pleasure",
        "comment": "Les deux pages gob.mx comptent.",
        "engine": "nvidia-deepseek",
    }
    allowed = {"https://a.example/list.pdf", "https://b.example/home"}
    merged = merge_picks(local, llm, allowed)
    assert merged["keep"] == ["https://a.example/list.pdf"]
    assert "https://invented.example/x" not in merged["keep"]
    assert merged["comment"].startswith("Les deux pages")
    assert merged["engine"] == "nvidia-deepseek"


def test_review_chain_and_chat_payload_vision():
    assert "review" in CHAINS
    jpeg = b"\xff\xd8\xff" + b"x" * 20
    body = chat_payload(
        "deepseek-ai/deepseek-v4-pro-0813", "sys", "hello", 32, images=[jpeg])
    content = body["messages"][1]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_render_screenshot_none_when_playwright_missing(monkeypatch):
    import app.core.render as render

    async def no_browser(log):
        return None

    monkeypatch.setattr(render, "_get_browser", no_browser)
    out = asyncio.run(render.render_screenshot("https://example.com"))
    assert out is None


def test_render_html_uses_isolated_worker_not_inprocess_browser(monkeypatch):
    import app.core.render as render

    called = {}

    def fake_worker(url, timeout_s, settle_ms):
        called["url"] = url
        return "<html>ok</html>"

    async def boom_browser(log):
        raise AssertionError("Chromium must not live in the API process")

    monkeypatch.setattr(render, "_run_render_worker", fake_worker)
    monkeypatch.setattr(render, "_get_browser", boom_browser)
    render._unavailable = False
    html = asyncio.run(render.render_html("https://example.org/fiche"))
    assert html == "<html>ok</html>"
    assert called["url"] == "https://example.org/fiche"


def test_cascade_retries_nim_text_when_vision_fails(monkeypatch):
    from app.core import judge

    calls = []

    async def tracked(*_a, **k):
        calls.append(k.get("images"))
        if k.get("images"):
            raise RuntimeError("vision 400")
        return {"ok": True}, "deepseek-ai/deepseek-v4-pro-0813"

    monkeypatch.setattr("app.core.nvidia.nvidia_enabled", lambda _s: True)
    monkeypatch.setattr("app.core.nvidia.complete_json_nvidia_tracked", tracked)
    monkeypatch.setattr(
        "app.core.nvidia.engine_label", lambda _m: "nvidia-deepseek-v4-pro")
    data, engine = asyncio.run(judge.complete_json_cascade(
        "sys", "user", {}, images=[b"\xff\xd8\xff"]))
    assert data == {"ok": True}
    assert engine == "nvidia-deepseek-v4-pro"
    assert calls[0]
    assert calls[1] is None


def test_suggest_writes_choices_not_gold(monkeypatch):
    db = _db()
    list_url = "https://gob.mx/list.pdf"
    news_url = "https://gob.mx/news"
    fiche = {
        "mrgid": 8313, "name": "Mexico", "iso2": "MX", "sovereign": "Mexico",
        "sources_td": [
            {"url": list_url, "official": True},
            {"url": news_url, "official": False},
        ],
        "ports": [],
    }

    async def fake_get_fiche(*_a, **_k):
        return {
            "fiche": fiche, "comment": "", "choices": {},
            "gold_on": False, "gold_ready": False,
        }

    async def fake_evidence(url, _log):
        keep = url == list_url
        return {
            "url": url,
            "text": "catalog" if keep else "news",
            "excerpt": "catalog" if keep else "news",
            "images": [b"\xff\xd8\xffxx"],
            "is_pdf": keep,
            "catalog_n": 5 if keep else 0,
            "looks_catalog": keep,
            "sufficient": keep,
            "bonus": 0.6 if keep else 0.0,
        }

    async def fake_llm(*_a, **k):
        assert k.get("role") == "review"
        assert k.get("images")
        return {
            "keep": [list_url],
            "drop": [news_url],
            "list_kind": "mixed_designated",
            "comment": "Le PDF gob.mx est la liste désignée.",
        }, "nvidia-deepseek"

    monkeypatch.setattr(
        "app.services.review_doc_picker.get_fiche", fake_get_fiche)
    monkeypatch.setattr(
        "app.services.review_doc_picker._evidence_for", fake_evidence)
    monkeypatch.setattr(
        "app.services.review_doc_picker.complete_json_cascade", fake_llm)

    out = asyncio.run(suggest_eez_documents(db, "8313", settings={}))
    assert out["choices"]["td"][list_url] == "keep"
    assert out["choices"]["td"][news_url] == "drop"
    assert out["comment"].startswith("Le PDF")
    assert out["engine"] == "nvidia-deepseek"
    assert out["gold_on"] is False
    assert out["gold_ready"] is True
    assert out["wrote_poe_ports"] is False
    assert db.review_gold.docs == []
    assert db.review_suggest.docs
    assert db.review_suggest.docs[0]["keep"] == [list_url]


def test_suggest_falls_back_to_local_when_llm_fails(monkeypatch):
    db = _db()
    list_url = "https://gob.mx/list.pdf"
    fiche = {
        "mrgid": 8313, "name": "Mexico", "iso2": "MX",
        "sources_td": [{"url": list_url, "official": True}],
        "ports": [],
    }

    async def fake_get_fiche(*_a, **_k):
        return {
            "fiche": fiche, "comment": "", "choices": {},
            "gold_on": False,
        }

    async def fake_evidence(url, _log):
        return {
            "url": url, "text": "lista", "excerpt": "lista",
            "images": [], "is_pdf": True, "catalog_n": 8,
            "looks_catalog": True, "sufficient": True, "bonus": 0.6,
        }

    async def boom(*_a, **_k):
        raise RuntimeError("no llm")

    monkeypatch.setattr(
        "app.services.review_doc_picker.get_fiche", fake_get_fiche)
    monkeypatch.setattr(
        "app.services.review_doc_picker._evidence_for", fake_evidence)
    monkeypatch.setattr(
        "app.services.review_doc_picker.complete_json_cascade", boom)

    out = asyncio.run(suggest_eez_documents(db, "8313", settings={}))
    assert out["choices"]["td"][list_url] == "keep"
    assert out["engine"] == "local"
    assert out["gold_on"] is False
    assert db.review_gold.docs == []


def test_evidence_uses_playwright_full_page_for_html(monkeypatch):
    async def fake_cascade(url, keep_raw=False, log=None):
        return {"text": "liste ports", "is_pdf": False, "raw": None}

    async def fake_shot(url, log=None, **_k):
        assert url == "https://gob.mx/habilitados"
        return b"\xff\xd8\xffFULL"

    monkeypatch.setattr(
        "app.services.review_doc_picker.extract_cascade", fake_cascade)
    monkeypatch.setattr("app.core.render.render_screenshot", fake_shot)
    ev = asyncio.run(_evidence_for("https://gob.mx/habilitados", lambda _m: None))
    assert ev["images"] == [b"\xff\xd8\xffFULL"]
    assert ev["is_pdf"] is False


def test_evidence_uses_pdf_page_jpegs(monkeypatch):
    async def fake_cascade(url, keep_raw=False, log=None):
        assert keep_raw is True
        return {"text": "decreto", "is_pdf": True, "raw": b"%PDF-1.4"}

    monkeypatch.setattr(
        "app.services.review_doc_picker.extract_cascade", fake_cascade)
    monkeypatch.setattr(
        "app.services.review_doc_picker.pdf_page_jpegs",
        lambda raw, n: [b"\xff\xd8\xffP0", b"\xff\xd8\xffP1"])
    ev = asyncio.run(_evidence_for("https://gob.mx/list.pdf", lambda _m: None))
    assert ev["is_pdf"] is True
    assert ev["images"] == [b"\xff\xd8\xffP0", b"\xff\xd8\xffP1"]


def test_remember_review_pins_mrgid_before_iso2(monkeypatch):
    exc = {
        "seed_urls": {"MX": ["https://gob.mx/country"]},
        "seed_urls_mrgid": {},
        "blacklist_urls_mrgid": {},
        "blacklist_domains_mrgid": {},
    }
    monkeypatch.setattr("app.services.poe_pipeline.load_exceptions", lambda: exc)
    out = remember_review_pins(
        8313,
        ["https://gob.mx/cms/habilitados.pdf"],
        ["https://gob.mx/news"],
        persist=False,
    )
    assert out["kept"] == ["https://gob.mx/cms/habilitados.pdf"]
    pins = seed_url_candidates({"mrgid": 8313, "iso2": "MX"}, exc)
    assert pins[0]["url"] == "https://gob.mx/cms/habilitados.pdf"
    assert any(p["url"] == "https://gob.mx/country" for p in pins)
    assert all(p["url"] != "https://gob.mx/news" for p in pins)


def test_extract_gold_fills_snapshot_not_poe_ports(monkeypatch):
    review_gold.reset_eez_pre_gold_cache()
    db = _db()
    _prepare_france_gold(db)
    asyncio.run(review_gold.toggle_gold(db, "eez", "5677"))
    n_ports = len(db.poe_ports.docs)

    async def fake_cascade(url, log=None, **kwargs):
        return {"text": "catalog", "is_pdf": True, "raw": None}

    monkeypatch.setattr(
        "app.services.review_extract.extract_cascade", fake_cascade)
    monkeypatch.setattr(
        "app.services.review_extract.extract_structured_ports",
        lambda text: [{
            "name": "Puerto Cortés", "city": None,
            "lat": 15.85, "lon": -87.94, "extraction_engine": "catalog",
        }],
    )
    out = asyncio.run(extract_gold_ports(db, "5677"))
    assert out["wrote_poe_ports"] is False
    assert out["ports_status"] == "extracted"
    assert out["port_count"] >= 1
    snap = db.review_gold.docs[0]["snapshot"]
    assert snap["ports_status"] == "extracted"
    assert snap["ports"]
    assert len(db.poe_ports.docs) == n_ports
    visible = asyncio.run(review_gold.visible_poe_port_docs(db, mrgid=5677))
    assert visible
    assert all(str(d["_id"]).startswith("gold:5677:") for d in visible)


def test_compare_and_fewshot_lessons():
    from app.services.review_lessons import (
        compare_verdicts, format_lessons_for_prompt, pick_fewshot,
        token_scores_from_lessons, url_lesson_delta,
    )

    cmp = compare_verdicts(
        ["https://gob.mx/habilitados.pdf"],
        ["https://gob.mx/news"],
        ["https://gob.mx/habilitados.pdf", "https://gob.mx/news"],
        [],
    )
    assert cmp["error_count"] == 1
    assert cmp["errors"][0]["url"] == "https://gob.mx/news"
    assert cmp["errors"][0]["proposer"] == "keep"
    assert cmp["errors"][0]["human"] == "drop"

    lessons = [{
        "entity_id": "8313", "label": "Mexico", "iso2": "MX",
        "sovereign": "Mexico", "had_proposal": True, "error_count": 1,
        "human_keep": ["https://gob.mx/cms/habilitados.pdf"],
        "human_drop": ["https://gob.mx/prensa/news"],
        "errors": [{
            "url": "https://gob.mx/prensa/news",
            "proposer": "keep", "human": "drop",
        }],
        "golded_at": "2026-09-14T00:00:00Z",
    }]
    few = pick_fewshot(lessons, {"mrgid": 5677, "iso2": "MX",
                                 "sovereign": "Mexico"})
    assert few and few[0]["entity_id"] == "8313"
    blob = format_lessons_for_prompt(few)
    assert "habilitados.pdf" in blob
    assert "Écarts" in blob
    scores = token_scores_from_lessons(lessons)
    assert url_lesson_delta("https://other.gob.mx/cms/habilitados-2024.pdf",
                            scores) > 0
    assert url_lesson_delta("https://other.gob.mx/prensa/news", scores) < 0


def test_gold_records_proposer_miss_and_report():
    from app.services.review_choices import save_choice
    from app.services.review_lessons import save_proposal
    from app.services.review_report import build_report, report_markdown

    review_gold.reset_eez_pre_gold_cache()
    db = _db()
    packed = asyncio.run(review_queue.get_fiche(db, "eez", "published", "5677"))
    td0 = packed["fiche"]["sources_td"][0]["url"]
    noise = "https://bad.example/annuaire-news"
    asyncio.run(save_proposal(db, "5677", {
        "keep": [td0, noise],
        "drop": [],
        "local_keep": [td0],
        "engine": "nvidia-deepseek",
        "comment": "J'ai tout gardé.",
        "list_kind": "mixed_designated",
    }, packed["fiche"]))
    asyncio.run(save_choice(db, "eez", "5677", "td", "keep", url=td0))
    asyncio.run(save_choice(db, "eez", "5677", "td", "drop", url=noise))
    ready = asyncio.run(review_queue.get_fiche(db, "eez", "published", "5677"))
    asyncio.run(review_gold.toggle_gold(
        db, "eez", "5677",
        fiche=ready["fiche"],
        comment=ready.get("comment") or "",
        choices=ready["choices"],
    ))
    lessons = db.review_lessons.docs
    assert lessons
    assert lessons[0]["had_proposal"] is True
    urls = {e["url"] for e in lessons[0]["errors"]}
    assert noise in urls
    assert any(e["proposer"] == "keep" and e["human"] == "drop"
               for e in lessons[0]["errors"] if e["url"] == noise)

    rep = asyncio.run(build_report(db, "eez"))
    misses = rep["pipeline_actions"]["proposer_errors"]
    assert any(m["url"] == noise for m in misses)
    assert rep["summary"]["eez"]["proposer_errors"] >= 1
    md = report_markdown(rep)
    assert "Proposer s'est trompé ici" in md
    assert "annuaire-news" in md


def test_batch_proposer_runs_all_fiches(monkeypatch):
    from app.core.tasks import TaskState
    from app.services.review_doc_picker import run_suggest_batch

    db = _db()
    called = []

    async def fake_suggest(db, eid, **_k):
        called.append(str(eid))
        return {"id": eid, "engine": "local", "choices": {"td": {}}}

    monkeypatch.setattr(
        "app.services.review_doc_picker.suggest_eez_documents", fake_suggest)
    state = TaskState()
    out = asyncio.run(run_suggest_batch(db, state, settings={}))
    assert "5677" in called
    assert "48944" in called
    assert out["ok"] == len(called)
    assert state.progress == len(called)
    assert state.summary["ok"] == len(called)


def test_llm_prompt_includes_gold_lessons(monkeypatch):
    db = _db()
    list_url = "https://gob.mx/list.pdf"
    fiche = {
        "mrgid": 8429, "name": "Mexico", "iso2": "MX", "sovereign": "Mexico",
        "sources_td": [{"url": list_url, "official": True}],
        "ports": [],
    }
    lessons = [{
        "entity_id": "8313", "label": "Mexico Pacific", "iso2": "MX",
        "sovereign": "Mexico", "had_proposal": True, "error_count": 1,
        "human_keep": ["https://gob.mx/cms/habilitados.pdf"],
        "human_drop": ["https://gob.mx/prensa/news"],
        "errors": [],
        "golded_at": "2026-09-14T00:00:00Z",
    }]

    async def fake_get_fiche(*_a, **_k):
        return {"fiche": fiche, "comment": "", "choices": {}, "gold_on": False}

    async def fake_evidence(url, _log):
        return {
            "url": url, "text": "lista", "excerpt": "lista",
            "images": [b"\xff\xd8\xff"], "is_pdf": True, "catalog_n": 4,
            "looks_catalog": True, "sufficient": True, "bonus": 0.5,
        }

    seen = {}

    async def fake_llm(system, prompt, settings, **k):
        seen["prompt"] = prompt
        return {
            "keep": [list_url], "drop": [],
            "list_kind": "mixed_designated",
            "comment": "Liste officielle.",
        }, "nvidia-deepseek"

    monkeypatch.setattr(
        "app.services.review_doc_picker.get_fiche", fake_get_fiche)
    monkeypatch.setattr(
        "app.services.review_doc_picker._evidence_for", fake_evidence)
    monkeypatch.setattr(
        "app.services.review_doc_picker.complete_json_cascade", fake_llm)
    asyncio.run(suggest_eez_documents(
        db, "8429", settings={}, lessons=lessons))
    assert "habilitados.pdf" in seen["prompt"]
    assert "Leçons Gold" in seen["prompt"]
