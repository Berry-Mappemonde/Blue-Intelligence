"""Repository paths only: no environment, configuration or filesystem writes."""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent
LOGS_DIR = REPO_ROOT / "logs"
SAMPLE_DATA_DIR = BACKEND_DIR / "data" / "sample"
