"""Shared repository root resolution.

Single source of truth for repo root to avoid fragile `parents[N]` chains.
"""
from pathlib import Path


def get_repo_root() -> Path:
    """Return the repository root (directory containing backend/, frontend/, etc.)."""
    # This file lives at backend/app/core/paths.py -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def get_backend_root() -> Path:
    """Return the backend/ directory."""
    return get_repo_root() / "backend"


def get_data_dir() -> Path:
    """Return the data/ directory (created if needed)."""
    return get_repo_root() / "data"


def get_logs_dir() -> Path:
    """Return the logs/ directory (created if needed)."""
    return get_repo_root() / "logs"