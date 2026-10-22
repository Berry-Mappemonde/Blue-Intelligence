#!/usr/bin/env python3
"""Programmatic entry point for the PoE Reconciler (JSON in, JSON out).

  python backend/run.py --input input_examples/01_bermuda.json [--output out.json]
  python backend/run.py --serve        # POST /run and GET /healthz on PORT (default 8000)

Works from a fresh clone with no credentials and no MongoDB: the repo-root .env
and backend/.env are loaded if present (never overriding the real environment),
Mongo defaults satisfy app.config at import (the pipeline never connects), and
SAMPLE_MODE is switched on when Zetaris or Meterless credentials are missing.
Trace events go to stdout as JSONL, then the result JSON; logs go to stderr.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
LOG = logging.getLogger('run')
_CREDENTIALS = {
    'Zetaris': (('ZETARIS_API_KEY',), ('ZETARIS_ORG_ID',)),
    'Meterless': (('METERLESS_RUNTIME_TOKEN', 'MODEL_API_KEY'),),
}


def prepare_environment(load_env_files: bool = True) -> None:
    """Run before any app import: .env files, Mongo defaults, SAMPLE_MODE switch."""
    if load_env_files:
        from dotenv import load_dotenv
        for path in (REPO_ROOT / '.env', BACKEND_DIR / '.env'):
            if path.is_file():
                load_dotenv(path)  # never overrides variables already set
    # app.config reads these at import time; the pipeline itself never connects.
    os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
    os.environ.setdefault('DB_NAME', 'bi_local')
    missing = [' or '.join(names) for groups in _CREDENTIALS.values() for names in groups
               if not any(os.environ.get(name, '').strip() for name in names)]
    if os.environ.get('SAMPLE_MODE', '').strip():
        LOG.info('SAMPLE_MODE=%s (set explicitly)', os.environ['SAMPLE_MODE'])
    elif missing:
        os.environ['SAMPLE_MODE'] = 'true'
        LOG.warning('SAMPLE_MODE enabled automatically; missing: %s', ', '.join(missing))
    else:
        LOG.info('Live mode: Zetaris and Meterless credentials found')
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))


def _read_input(arg: str) -> dict:
    path = Path(arg)
    if not path.is_file() and not path.is_absolute() and (REPO_ROOT / path).is_file():
        path = REPO_ROOT / path
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('input must be a JSON object: {"zone_name": str, "run_id": optional str}')
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--input', help='JSON file: {"zone_name": str, "run_id": optional str}')
    mode.add_argument('--serve', action='store_true', help='serve POST /run and GET /healthz')
    parser.add_argument('--output', help='also write the result JSON to this file')
    parser.add_argument('--no-dotenv', action='store_true',
                        help='ignore .env files (simulates a fresh clone)')
    args = parser.parse_args(argv)
    level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(level=getattr(logging, level, logging.INFO), stream=sys.stderr,
                        format='%(levelname)s %(name)s: %(message)s')
    prepare_environment(load_env_files=not args.no_dotenv)

    if args.serve:
        import uvicorn
        from app.pipeline.api import app
        uvicorn.run(app, host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', '8000')))
        return 0

    import asyncio
    from app.pipeline.run_pipeline import run_pipeline, validate_input
    try:
        data = _read_input(args.input)
        zone_name, run_id = validate_input(data.get('zone_name'), data.get('run_id'))
    except (OSError, ValueError) as exc:
        LOG.error('Invalid input: %s', exc)
        return 2
    result = asyncio.run(run_pipeline(zone_name, run_id))
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text, flush=True)
    if args.output:
        Path(args.output).write_text(text + '\n', encoding='utf-8')
    return 1 if result['error'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
