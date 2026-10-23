"""Minimal HTTP surface for the pipeline: demo page, POST /run, zones, traces, health.

Separate from app.main (the production Blue Intelligence API), so judges can run
the agent product without MongoDB. Started by `python backend/run.py --serve`.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.pipeline.run_pipeline import list_zones, load_trace, run_pipeline

DEMO_PAGE = Path(__file__).with_name('demo_page.html')

app = FastAPI(title='Blue Intelligence PoE Reconciler', version='1.0')


class RunRequest(BaseModel):
    zone_name: str = Field(min_length=1, max_length=200, examples=['Bermuda'])
    run_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{1,64}$')


@app.get('/', response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> HTMLResponse:
    """Self-contained demo page (inline CSS and JS, no network dependencies)."""
    return HTMLResponse(DEMO_PAGE.read_text(encoding='utf-8'))


@app.post('/run')
async def run(request: RunRequest) -> dict:
    """JSON in, JSON out. A timeout or step failure returns a partial result with `error`."""
    return await run_pipeline(request.zone_name, request.run_id)


@app.get('/zones')
def zones() -> dict:
    """Zones available in the current mode (sync: FastAPI runs it in a worker thread)."""
    return list_zones()


@app.get('/runs/{run_id}/trace')
def run_trace(run_id: str) -> dict:
    """Trace events of the latest run with this run_id, as JSON."""
    try:
        events = load_trace(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    if not events:
        raise HTTPException(status_code=404, detail='no trace for this run_id')
    return {'run_id': run_id, 'events': events}


@app.get('/healthz')
def healthz() -> dict:
    return {'status': 'ok', 'sample_mode': os.environ.get('SAMPLE_MODE', '').strip().lower() == 'true'}
