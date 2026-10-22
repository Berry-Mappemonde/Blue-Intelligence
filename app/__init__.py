"""Root application package with access to the existing backend modules.

The scorer imports app.core and app.config internally. Extend this package's
search path so those imports resolve without changing the global sys.path.
Root modules take precedence over modules in backend/app.
"""
from pathlib import Path

__path__.append(str(Path(__file__).resolve().parents[1] / "backend" / "app"))
