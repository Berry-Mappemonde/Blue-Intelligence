"""
render_core — Rendu navigateur local (Playwright + Chromium headless).

``render_html`` (cascade Complet / PoE) et ``render_screenshot`` (vision
Review) lancent Chromium dans un *sous-processus* (``app.core.render_worker``).
Un crash natif (munmap_chunk sous MemoryHigh=2G) ou un site qui ne finit
jamais de se charger tue uniquement l'enfant : l'API continue, la RAM
est rendue. Le groupe de process (Python + Chrome) est tué au délai.

Dégradation propre : si playwright ou son navigateur n'est pas installé,
on retourne None et la cascade continue sans rendu.
Installation : pip install playwright && playwright install chromium
"""
import asyncio
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from app.config import BACKEND_DIR

UA_BROWSER = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_pw = None
_browser = None
_lock = asyncio.Lock()
# Un Chromium à la fois dans le cgroup MemoryHigh=2G.
_sem = asyncio.Semaphore(1)
_unavailable = False
RENDER_SUBPROCESS_GRACE_S = 20
SCREENSHOT_MAX_HEIGHT = 2400


class RenderUnavailable(Exception):
    """Playwright / navigateur absent — désactive les rendus suivants."""


def _render_worker_env() -> dict:
    env = os.environ.copy()
    backend = str(BACKEND_DIR)
    current = env.get("PYTHONPATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if backend not in parts:
        env["PYTHONPATH"] = os.pathsep.join([backend, *parts]) if parts else backend
    return env


def _kill_worker_group(proc: subprocess.Popen) -> None:
    """Tue Python + Chromium (session setsid), pas seulement le père."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass


def _run_worker_argv(argv: list[str], timeout_s: int) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "app.core.render_worker", *argv]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_render_worker_env(),
        cwd=str(BACKEND_DIR),
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s + RENDER_SUBPROCESS_GRACE_S)
    except subprocess.TimeoutExpired:
        _kill_worker_group(proc)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            stdout, stderr = b"", b""
        raise subprocess.TimeoutExpired(cmd, timeout_s + RENDER_SUBPROCESS_GRACE_S,
                                        output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def _decode_worker(proc: subprocess.CompletedProcess) -> None:
    if proc.returncode == 2:
        err = (proc.stderr or b"").decode("utf-8", "replace")[:200]
        raise RenderUnavailable(err or "playwright missing")


def _run_render_worker(url: str, timeout_s: int, settle_ms: int) -> str | None:
    """Spawn ``app.core.render_worker`` HTML — hookable depuis les tests."""
    with tempfile.TemporaryDirectory(prefix="bi-render-") as tmp:
        out = Path(tmp) / "page.html"
        try:
            proc = _run_worker_argv(
                [url, str(out), str(timeout_s), str(settle_ms)], timeout_s)
        except subprocess.TimeoutExpired:
            return None
        _decode_worker(proc)
        if proc.returncode != 0 or not out.is_file():
            return None
        text = out.read_text(encoding="utf-8")
        return text or None


def _run_screenshot_worker(url: str, timeout_s: int, settle_ms: int,
                           max_height: int = SCREENSHOT_MAX_HEIGHT) -> bytes | None:
    """Spawn ``app.core.render_worker --screenshot`` — hookable depuis les tests."""
    with tempfile.TemporaryDirectory(prefix="bi-shot-") as tmp:
        out = Path(tmp) / "page.jpg"
        try:
            proc = _run_worker_argv(
                ["--screenshot", url, str(out), str(timeout_s),
                 str(settle_ms), str(max_height)],
                timeout_s)
        except subprocess.TimeoutExpired:
            return None
        _decode_worker(proc)
        if proc.returncode != 0 or not out.is_file():
            return None
        data = out.read_bytes()
        return data or None


async def _get_browser(log):
    """Ancien navigateur partagé — plus utilisé pour les captures Review."""
    global _pw, _browser, _unavailable
    if _unavailable:
        return None
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        try:
            from playwright.async_api import async_playwright
            if _pw is None:
                _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage",
                                     "--disable-gpu", "--renderer-process-limit=1"])
            return _browser
        except Exception as e:
            _unavailable = True
            log(f"render: Playwright indisponible ({type(e).__name__}: {str(e)[:80]}) — rendu désactivé")
            return None


async def render_html(url: str, timeout_s: int = 45, settle_ms: int = 2500, log=None) -> str | None:
    """HTML rendu par Chromium isolé (DOM après JavaScript), ou None."""
    global _unavailable
    log = log or (lambda m: None)
    if _unavailable:
        return None
    async with _sem:
        try:
            return await asyncio.to_thread(
                _run_render_worker, url, timeout_s, settle_ms)
        except RenderUnavailable as e:
            _unavailable = True
            log(f"render: Playwright indisponible ({e}) — rendu désactivé")
            return None
        except Exception as e:
            log(f"render {url[:70]}: échec ({type(e).__name__}: {str(e)[:60]})")
            return None


async def render_screenshot(url: str, timeout_s: int = 45, settle_ms: int = 2500,
                            log=None) -> bytes | None:
    """Capture JPEG bornée (vision Review) dans un sous-processus, ou None."""
    global _unavailable
    from app.core.extract import should_skip_screenshot
    log = log or (lambda m: None)
    skip = should_skip_screenshot(url)
    if skip:
        log(f"screenshot {url[:70]}: sauté ({skip})")
        return None
    if _unavailable:
        return None
    async with _sem:
        try:
            return await asyncio.to_thread(
                _run_screenshot_worker, url, timeout_s, settle_ms,
                SCREENSHOT_MAX_HEIGHT)
        except RenderUnavailable as e:
            _unavailable = True
            log(f"render: Playwright indisponible ({e}) — rendu désactivé")
            return None
        except Exception as e:
            log(f"screenshot {url[:70]}: échec ({type(e).__name__}: {str(e)[:60]})")
            return None


async def shutdown_render():
    """Fermeture propre (appelée au shutdown de l'app et après chaque fiche)."""
    global _pw, _browser
    try:
        if _browser is not None:
            await _browser.close()
        if _pw is not None:
            await _pw.stop()
    except Exception:
        pass
    _browser = None
    _pw = None
