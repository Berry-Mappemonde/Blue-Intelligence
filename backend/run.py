#!/usr/bin/env python3
"""Blue Intelligence CLI - Port verification pipeline runner.

Usage: python run.py --zone "Zone Name" --run-id RUN123 [--sample-mode]

This script runs a single cycle of the PoE verification pipeline via the
FastAPI application. It is NOT a web server - use uvicorn app.main:app for
the official API on port 8001.

This is the SINGLE application - no parallel servers needed.
"""
import argparse
import asyncio
import os
import re
import sys
import uuid
from pathlib import Path

# Ensure we can import from the backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.run_pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Blue Intelligence CLI")
    parser.add_argument("--zone", required=True, help="EEZ zone name to verify")
    parser.add_argument("--run-id", help="Run ID (generated if not provided)")
    parser.add_argument("--sample-mode", action="store_true",
                        help="Run in sample mode (offline, no API keys needed)")
    parser.add_argument("--timeout", type=float, default=300.0,
                        help="Pipeline timeout in seconds (default: 300)")
    parser.add_argument("--trace", help="Custom trace log path prefix")

    args = parser.parse_args()

    # Set SAMPLE_MODE if requested (enables offline reproducibility)
    if args.sample_mode:
        os.environ["SAMPLE_MODE"] = "true"
        print("SAMPLE_MODE enabled - offline reproducible mode")

    # Generate run_id if not provided
    run_id = args.run_id or str(uuid4())
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', run_id):
        print(f"Warning: run_id '{run_id}' may not match expected format")

    # Set trace path if provided
    if args.trace:
        os.environ["TRACE_LOG_PATH"] = args.trace

    # Run the pipeline
    print("Starting Blue Intelligence Pipeline")
    print(f"Zone: {args.zone}")
    print(f"Run ID: {run_id}")
    print(f"Mode: {'sample (offline)' if args.sample_mode else 'live'}")
    print(f"Timeout: {args.timeout}s")
    print()

    async def run():
        result = await run_pipeline(args.zone, run_id)
        return result

    result = asyncio.run(run())

    # Print summary
    print("Pipeline Result")
    print(f"Run ID:   {result['run_id']}")
    print(f"Zone:     {result['zone']}")
    print(f"Mode:     {result['mode']}")
    print(f"Ports:    {len(result['ports'])}")
    print(f"Summary:  {result.get('summary', {})}")
    print(f"Brief:    {len(result.get('brief') or '')} chars")

    if result.get('llm'):
        llm = result['llm']
        print(f"LLM:      {llm.get('provider', 'N/A')} / {llm.get('model', 'N/A')}")
        if llm.get('fallback_reason'):
            print(f"Fallback:  {llm['fallback_reason']}")

    if result.get('error'):
        print(f"Error: {result['error']}")

    if result.get('memory'):
        mem = result['memory']
        print(f"Memory:   {mem.get('recalled', 0)} recalled, "
              f"{'remembered' if mem.get('remembered') else 'not remembered'}")

    print("Done.")

    # Return 0 if success, 1 if error
    return 0 if not result.get('error') else 1


if __name__ == "__main__":
    sys.exit(main() or 0)