"""Nightshift-first generation, with NVIDIA Nemotron and offline fallbacks.

Environment (no credentials are required for SAMPLE_MODE):
  MODEL_BASE_URL: Nightshift OpenAI base, default http://127.0.0.1:8088/v1
  MODEL_API_KEY: Nightshift bearer token; blank permits an unauthenticated probe
  MODEL_NAME: Nightshift route/model, default meterless/fast. Configure this route
    in Nightshift to serve Nemotron; response.model is recorded without guessing.
  NVIDIA_API_KEY: optional direct NVIDIA fallback bearer token
  NEMOTRON_MODEL: default nvidia/nemotron-3.5-lightning-30b-a3b
  SAMPLE_MODE: true bypasses all providers (JSON result is {"ports": []})
  LLM_PROVIDER: meterless opts existing ask_json/ask_text into this generator
  TRACE_LOG_PATH: override repo logs/trace-<run_id>.jsonl
  TRACE_STDOUT: 0 disables stdout traces (default 1)
  NIGHTSHIFT_LIVE: 1 enables the opt-in live Nemotron integration test

JSON mode requires an object, matching ask_json's contract. Sample responses
contain no invented port or clearance facts. Provider failures are returned as
sanitized fallback reasons, never raw HTTP bodies or exception messages.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import weakref
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from app.core.llm import parse_json_flexible

DEFAULT_BASE_URL = 'http://127.0.0.1:8088/v1'
DEFAULT_MODEL = 'meterless/fast'
DEFAULT_NEMOTRON_MODEL = 'nvidia/nemotron-3.5-lightning-30b-a3b'
NVIDIA_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
DEFAULT_TRACE_LOG_DIR = Path(__file__).resolve().parents[3] / 'logs'
_PROBE_TTL = 60
_probe_cache = {}  # One configuration at a time; includes a credential fingerprint.
_probe_locks = weakref.WeakKeyDictionary()


def _env(name, default=''):
    return os.environ.get(name, '').strip() or default


class _ProviderFailure(Exception):
    """Carries a safe reason code, never a provider response body."""


async def _request(client, method, url, **kwargs):
    for attempt in range(3):  # initial attempt plus two retries
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            reason = 'timeout' if isinstance(exc, httpx.TimeoutException) else 'offline'
            if attempt == 2:
                raise _ProviderFailure(reason) from None
        else:
            if response.status_code in (401, 403):
                raise _ProviderFailure('unauthorized')
            if 200 <= response.status_code < 300:
                return response
            if response.status_code < 500 or attempt == 2:
                raise _ProviderFailure(f'http_{response.status_code}')
        await asyncio.sleep(2 ** attempt)
    raise AssertionError('unreachable')


async def _probe(client, base, key, headers):
    identity = (base, hashlib.sha256(key.encode()).hexdigest())
    loop = asyncio.get_running_loop()
    lock = _probe_locks.setdefault(loop, asyncio.Lock())
    async with lock:
        cached = _probe_cache.get(identity)
        if cached and time.monotonic() - cached[0] < _PROBE_TTL:
            return cached[1]
        try:
            await _request(client, 'GET', base + '/models', headers=headers)
            status = 'ready'
        except _ProviderFailure as exc:
            status = str(exc)
        _probe_cache.clear()
        _probe_cache[identity] = (time.monotonic(), status)
        return status


async def _complete(client, url, headers, model, prompt, system, json_mode):
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    if json_mode:
        messages.append({'role': 'system', 'content': 'Return a single valid JSON object.'})
    messages.append({'role': 'user', 'content': prompt})
    payload = dict(model=model, messages=messages, temperature=0, stream=False, max_tokens=2000)
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}
    response = await _request(client, 'POST', url, headers=headers, json=payload)
    try:
        body = response.json()
        text = body['choices'][0]['message']['content']
        served_model = body['model']
        if not isinstance(text, str) or not text.strip() or not isinstance(served_model, str) or not served_model:
            raise ValueError
    except (ValueError, KeyError, IndexError, TypeError):
        raise _ProviderFailure('invalid_response') from None
    result = dict(text=text, model=served_model)
    if json_mode:
        parsed = parse_json_flexible(text)
        if not isinstance(parsed, dict):
            raise _ProviderFailure('invalid_json')
        result['parsed'] = parsed
    return result


def _sample(prompt, json_mode):
    if json_mode:
        return dict(text='{"ports": []}', parsed={'ports': []}, model='deterministic-heuristic')
    maritime = bool(re.search(r'\b(port|ports|customs|maritime|clearance)\b', prompt, re.I))
    subject = 'port verification' if maritime else 'this request'
    return dict(text=f'Sample mode: no AI provider used. No verified information is available for {subject}.',
                model='deterministic-heuristic')


def _trace(result, prompt, role, requested_model):
    entry = dict(timestamp=datetime.now(timezone.utc).isoformat(), agent_name='MeterlessGenerator',
                 action='generate', run_id=result['run_id'], provider=result['provider'],
                 requested_model=requested_model, served_model=result['model'],
                 duration_ms=result['duration_ms'], status=result['status'],
                 input_summary={'prompt': prompt[:200], 'role': role},
                 fallback_reason=result.get('fallback_reason'))
    # Redact before truncating too, so even a key straddling the 200-char limit
    # cannot appear as a prefix in a prompt preview.
    preview = prompt
    for name in ('MODEL_API_KEY', 'NVIDIA_API_KEY'):
        secret = _env(name)
        if secret:
            preview = preview.replace(secret, '[REDACTED]')
    entry['input_summary']['prompt'] = preview[:200]
    payload = json.dumps(entry, ensure_ascii=False)
    for name in ('MODEL_API_KEY', 'NVIDIA_API_KEY'):
        secret = _env(name)
        if secret:
            payload = payload.replace(json.dumps(secret, ensure_ascii=False)[1:-1], '[REDACTED]')
    path = Path(_env('TRACE_LOG_PATH') or DEFAULT_TRACE_LOG_DIR / f"trace-{result['run_id']}.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(payload + '\n')
    if _env('TRACE_STDOUT', '1') != '0':
        print(payload, flush=True)


async def generate(prompt, system=None, *, json_mode=False, role='json', run_id=None) -> dict:
    """Generate via Nightshift first; return honest provider/model provenance.

    duration_ms includes probes, retries and fallbacks. run_id is generated if
    omitted and returned to the caller. Sample output has status='sample' and
    sample=True, including when all configured providers fail.
    """
    run_id = str(uuid4()) if run_id is None else run_id
    if not isinstance(run_id, str) or re.fullmatch(r'[A-Za-z0-9_-]+', run_id) is None:
        raise ValueError('run_id must contain only letters, digits, underscores or hyphens')
    started = time.monotonic()
    reasons, result, provider = [], None, 'sample'
    requested_model = _env('MODEL_NAME', DEFAULT_MODEL)
    if _env('SAMPLE_MODE').lower() == 'true':
        reasons.append('SAMPLE_MODE=true')
    else:
        base = _env('MODEL_BASE_URL', DEFAULT_BASE_URL).rstrip('/')
        key = _env('MODEL_API_KEY')
        headers = {'meterless-app': 'blue-intelligence', 'meterless-scope': 'user'}
        if key:
            headers['Authorization'] = f'Bearer {key}'
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
            status = await _probe(client, base, key, headers)
            if status == 'ready':
                try:
                    result = await _complete(client, base + '/chat/completions', headers,
                                             requested_model, prompt, system, json_mode)
                    provider = 'nightshift'
                except _ProviderFailure as exc:
                    reasons.append(f'nightshift: {exc}')
            else:
                reasons.append(f'nightshift: {status}')
            if result is None:
                nvidia_key = _env('NVIDIA_API_KEY')
                if nvidia_key:
                    requested_model = _env('NEMOTRON_MODEL', DEFAULT_NEMOTRON_MODEL)
                    try:
                        result = await _complete(client, NVIDIA_URL,
                            {'Authorization': f'Bearer {nvidia_key}'}, requested_model, prompt, system, json_mode)
                        provider = 'nvidia'
                    except _ProviderFailure as exc:
                        reasons.append(f'nvidia: {exc}')
                else:
                    reasons.append('nvidia: missing_key')
    if result is None:
        result = _sample(prompt, json_mode)
    result.update(provider=provider, run_id=run_id, sample=provider == 'sample',
                  status='sample' if provider == 'sample' else 'success',
                  duration_ms=round((time.monotonic() - started) * 1000, 3))
    if reasons:
        result['fallback_reason'] = '; '.join(reasons)
    _trace(result, prompt, role, requested_model)
    return result
