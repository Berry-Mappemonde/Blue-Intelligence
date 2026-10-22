"""Offline provider orchestration plus opt-in real Nightshift/Nemotron proof."""
import asyncio
import json
import os
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core import generator, llm


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path, request):
    generator._probe_cache.clear()
    generator._probe_locks.clear()
    monkeypatch.setenv('TRACE_LOG_PATH', str(tmp_path / 'trace.jsonl'))
    monkeypatch.setenv('TRACE_STDOUT', '1')
    if request.node.name != 'test_live_nightshift_nemotron':
        for name in ('SAMPLE_MODE', 'MODEL_NAME', 'NEMOTRON_MODEL', 'LLM_PROVIDER'):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv('MODEL_BASE_URL', generator.DEFAULT_BASE_URL)
        monkeypatch.setenv('MODEL_API_KEY', 'nightshift-test-secret')
        monkeypatch.setenv('NVIDIA_API_KEY', 'nvidia-test-secret')
        monkeypatch.setattr(generator.asyncio, 'sleep', AsyncMock())
        # Tests must explicitly install a transport; otherwise network is forbidden.
        monkeypatch.setattr(httpx.AsyncClient, 'send', AsyncMock(side_effect=AssertionError('Unexpected network')))
    yield tmp_path / 'trace.jsonl'
    generator._probe_cache.clear()
    generator._probe_locks.clear()


@pytest.fixture
def transport(monkeypatch):
    original = httpx.AsyncClient
    # Restore send for MockTransport clients only, bypassing the network guard.
    original_send = _ORIGINAL_SEND
    requests = []

    def install(handler):
        def dispatch(request):
            requests.append(request)
            return handler(request)

        class MockClient(original):
            send = original_send

        def factory(**kwargs):
            assert kwargs['timeout'].read == 180
            return MockClient(transport=httpx.MockTransport(dispatch), **kwargs)
        monkeypatch.setattr(generator.httpx, 'AsyncClient', factory)
        return requests
    return install


_ORIGINAL_SEND = httpx.AsyncClient.send


def answer(text='{"ports": []}', model='nvidia/nemotron-3.5-lightning-30b-a3b'):
    return httpx.Response(200, json={'model': model, 'choices': [{'message': {'content': text}}]})


def run(**kwargs):
    return asyncio.run(generator.generate('Extract ports from this source.', run_id='test-run', **kwargs))


def test_nightshift_success_headers_actual_model_and_trace(transport, isolated_environment, capsys):
    def handler(request):
        assert request.headers['Authorization'] == 'Bearer nightshift-test-secret'
        assert request.headers['meterless-app'] == 'blue-intelligence'
        assert request.headers['meterless-scope'] == 'user'
        if request.method == 'GET':
            assert request.url.path == '/v1/models'
            return httpx.Response(200, json={'data': [{'id': 'meterless/fast'}]})
        payload = json.loads(request.content)
        assert payload['model'] == 'meterless/fast'
        assert payload['response_format'] == {'type': 'json_object'}
        return answer('```json\n{"ports": [{"name": "Papeete"}]}\n```')
    requests = transport(handler)
    result = run(json_mode=True)
    assert result['provider'] == 'nightshift'
    assert 'nemotron' in result['model']
    assert result['parsed']['ports'][0]['name'] == 'Papeete'
    assert len(requests) == 2
    entry = json.loads(isolated_environment.read_text())
    assert entry['agent_name'] == 'MeterlessGenerator'
    assert entry['requested_model'] == 'meterless/fast'
    assert entry['served_model'] == result['model']
    assert entry['run_id'] == 'test-run' and entry['status'] == 'success'
    assert entry['duration_ms'] >= 0
    assert capsys.readouterr().out == isolated_environment.read_text()


def test_offline_nightshift_nvidia_fallback(transport):
    def handler(request):
        if request.url.host == '127.0.0.1':
            raise httpx.ConnectError('secret body should never leak', request=request)
        assert request.headers['Authorization'] == 'Bearer nvidia-test-secret'
        assert 'meterless-app' not in request.headers
        assert json.loads(request.content)['model'] == generator.DEFAULT_NEMOTRON_MODEL
        return answer('Nemotron processed the port source.')
    requests = transport(handler)
    result = run()
    assert result['provider'] == 'nvidia'
    assert result['fallback_reason'] == 'nightshift: offline'
    assert len(requests) == 4
    assert 'parsed' not in result


def test_both_down_returns_explicit_sample(transport):
    requests = transport(lambda request: httpx.Response(503, text='private server body'))
    result = run(json_mode=True)
    assert len(requests) == 6
    assert result['provider'] == 'sample' and result['sample']
    assert result['parsed'] == {'ports': []}
    assert result['status'] == 'sample'
    assert result['fallback_reason'] == 'nightshift: http_503; nvidia: http_503'


@pytest.mark.parametrize('status', [401, 403])
def test_unauthorized_is_not_offline_and_does_not_retry(status, transport):
    requests = transport(lambda r: httpx.Response(status) if r.method == 'GET' else answer())
    result = run()
    assert result['provider'] == 'nvidia'
    assert result['fallback_reason'] == 'nightshift: unauthorized'
    assert len(requests) == 2


@pytest.mark.parametrize('failure', ['5xx', 'connection', 'timeout'])
def test_chat_retries_then_success(failure, transport):
    posts = []
    def handler(request):
        if request.method == 'GET':
            return httpx.Response(200, json={'data': []})
        posts.append(request)
        if len(posts) < 3:
            if failure == 'connection':
                raise httpx.ConnectError('offline', request=request)
            if failure == 'timeout':
                raise httpx.ReadTimeout('timeout', request=request)
            return httpx.Response(502)
        return answer()
    transport(handler)
    assert run()['provider'] == 'nightshift'
    assert len(posts) == 3
    assert [call.args[0] for call in generator.asyncio.sleep.call_args_list] == [1, 2]


def test_probe_cache_ttl_configuration_and_concurrent_calls(transport, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(generator.time, 'monotonic', lambda: now[0])
    requests = transport(lambda r: httpx.Response(200, json={'data': []}) if r.method == 'GET' else answer())
    async def calls():
        await asyncio.gather(*(generator.generate('port', run_id='cache') for _ in range(3)))
        assert sum(r.method == 'GET' for r in requests) == 1
        now[0] += 59
        await generator.generate('port')
        assert sum(r.method == 'GET' for r in requests) == 1
        now[0] += 2
        await generator.generate('port')
        assert sum(r.method == 'GET' for r in requests) == 2
        monkeypatch.setenv('MODEL_API_KEY', 'new-test-key')
        await generator.generate('port')
        assert sum(r.method == 'GET' for r in requests) == 3
    asyncio.run(calls())


def test_explicit_sample_never_uses_network(monkeypatch):
    monkeypatch.setenv('SAMPLE_MODE', 'true')
    first, second = run(json_mode=True), run(json_mode=True)
    assert first['text'] == second['text'] == '{"ports": []}'
    assert first['fallback_reason'] == 'SAMPLE_MODE=true'
    assert 'Sample mode' in run()['text']


def test_no_keys_offline_works(transport, monkeypatch):
    monkeypatch.delenv('MODEL_API_KEY')
    monkeypatch.delenv('NVIDIA_API_KEY')
    def handler(request):
        assert 'authorization' not in request.headers
        raise httpx.ConnectError('offline')
    transport(handler)
    result = run()
    assert result['provider'] == 'sample'
    assert 'missing_key' in result['fallback_reason']


def test_secrets_redacted_preview_truncated_and_stdout_switch(transport, isolated_environment, monkeypatch, capsys):
    transport(lambda r: httpx.Response(401, text='nightshift-test-secret nvidia-test-secret'))
    prompt = 'x' * 190 + 'nightshift-test-secret nvidia-test-secret ' + 'z' * 300
    asyncio.run(generator.generate(prompt, run_id='redact'))
    text = isolated_environment.read_text()
    assert 'nightshift-test-secret' not in text and 'nvidia-test-secret' not in text
    assert len(json.loads(text)['input_summary']['prompt']) <= 200
    assert capsys.readouterr().out == text
    monkeypatch.setenv('TRACE_STDOUT', '0')
    run()
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('response', [answer('not JSON'), httpx.Response(200, json={}),
                                   httpx.Response(200, text='not a response')])
def test_invalid_response_falls_back(response, transport):
    def handler(request):
        if request.method == 'GET':
            return httpx.Response(200, json={'data': []})
        return response if request.url.host == '127.0.0.1' else answer()
    transport(handler)
    assert run(json_mode=True)['provider'] == 'nvidia'


def test_default_trace_path_and_safe_run_id(monkeypatch, tmp_path):
    monkeypatch.setenv('SAMPLE_MODE', 'true')
    monkeypatch.delenv('TRACE_LOG_PATH')
    from pathlib import Path
    assert generator.DEFAULT_TRACE_LOG_DIR == Path(__file__).resolve().parents[2] / 'logs'
    monkeypatch.setattr(generator, 'DEFAULT_TRACE_LOG_DIR', tmp_path)
    result = run()
    assert json.loads((tmp_path / 'trace-test-run.jsonl').read_text())['run_id'] == result['run_id']
    with pytest.raises(ValueError, match='run_id'):
        asyncio.run(generator.generate('test', run_id='../outside'))


@pytest.mark.parametrize('provider', [None, 'auto', 'nvidia', 'openrouter'])
def test_llm_ask_json_unchanged_without_opt_in(monkeypatch, provider):
    from app.core import judge
    if provider:
        monkeypatch.setenv('LLM_PROVIDER', provider)
    cascade = AsyncMock(return_value=({'ports': []}, 'nvidia-gpt-oss'))
    monkeypatch.setattr(judge, 'complete_json_cascade', cascade)
    monkeypatch.setattr(generator, 'generate', AsyncMock(side_effect=AssertionError('Must not use generator')))
    settings = {'custom': 'setting'}
    assert asyncio.run(llm.ask_json('prompt', 'system', settings, max_tokens=123, role='extract')) == {'ports': []}
    cascade.assert_awaited_once_with('system', 'prompt', settings, role='extract', max_tokens=123, log=None)


@pytest.mark.skipif(os.environ.get('NIGHTSHIFT_LIVE') != '1', reason='Set NIGHTSHIFT_LIVE=1 for local Nightshift')
def test_live_nightshift_nemotron(monkeypatch):
    monkeypatch.setenv('SAMPLE_MODE', 'false')
    result = asyncio.run(generator.generate(
        'Extract only the port explicitly named in this source: "Papeete is a port of entry." '
        'Return JSON {"ports": [{"name": "..."}]}.', json_mode=True, run_id='nightshift-live'))
    assert result['provider'] == 'nightshift', result.get('fallback_reason')
    assert 'nemotron' in result['model'].lower(), result['model']
    assert result['parsed']['ports'][0]['name'].lower() == 'papeete'


@pytest.mark.parametrize('entrypoint', ['ask_json', 'ask_json_tracked', 'ask_text'])
def test_llm_meterless_opt_in(monkeypatch, entrypoint):
    monkeypatch.setenv('LLM_PROVIDER', 'meterless')
    generated = AsyncMock(return_value=dict(text='answer', parsed={'ports': []}, provider='nightshift'))
    monkeypatch.setattr(generator, 'generate', generated)
    function = getattr(llm, entrypoint)
    result = asyncio.run(function('prompt', 'system'))
    if entrypoint == 'ask_text':
        assert result == 'answer'
        generated.assert_awaited_once_with('prompt', 'system', role='text')
    else:
        assert result == (({'ports': []}, 'nightshift') if entrypoint == 'ask_json_tracked' else {'ports': []})
        generated.assert_awaited_once_with('prompt', 'system', json_mode=True, role='json')


def test_llm_text_default_preserves_nvidia_route(monkeypatch):
    from app.core import nvidia
    monkeypatch.setattr(nvidia, 'nvidia_enabled', lambda settings: True)
    complete = AsyncMock(return_value='original nvidia response')
    monkeypatch.setattr(nvidia, 'complete_text_nvidia', complete)
    monkeypatch.setattr(generator, 'generate', AsyncMock(side_effect=AssertionError('Must not use generator')))
    settings = {'custom': 'setting'}
    assert asyncio.run(llm.ask_text('prompt', 'system', settings, max_tokens=55)) == 'original nvidia response'
    complete.assert_awaited_once_with('system', 'prompt', settings, max_tokens=55)
