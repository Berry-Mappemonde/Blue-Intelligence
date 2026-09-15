"""
server.py — compatibility shim: the application lives in app/main.py.
Keeps the historical `uvicorn server:app` command working.
"""
from app.main import app  # noqa: F401
