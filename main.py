# Some platforms (Runflare included, it turns out) auto-detect a FastAPI app
# and run it assuming `main:app` at the project root - i.e. a top-level
# main.py with an `app` variable - rather than using this repo's Dockerfile.
# The real app lives in app/main.py; this just re-exports it so both
# conventions work without needing two copies of the app.
from app.main import app

__all__ = ["app"]
