"""Minimal HTTP surface for the pipeline: POST /run and GET /healthz.

Separate from app.main (the production Blue Intelligence API), so judges can run
the agent product without MongoDB. Started by `python backend/run.py --serve`.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.pipeline.run_pipeline import run_pipeline

app = FastAPI(title='Blue Intelligence PoE Reconciler', version='1.0')


class RunRequest(BaseModel):
    zone_name: str = Field(min_length=1, max_length=200, examples=['Bermuda'])
    run_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{1,64}$')


@app.post('/run')
async def run(request: RunRequest) -> dict:
    """JSON in, JSON out. A timeout or step failure returns a partial result with `error`."""
    return await run_pipeline(request.zone_name, request.run_id)


@app.get('/healthz')
def healthz() -> dict:
    return {'status': 'ok', 'sample_mode': os.environ.get('SAMPLE_MODE', '').strip().lower() == 'true'}
