"""Kinsum local server.

Serves the API under /api and the built frontend (frontend/dist) for everything else.
It listens on 127.0.0.1 only, so no other device on the network can connect.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import REPO_ROOT, settings

app = FastAPI(title="Kinsum", version=__version__)

FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


@app.get("/api/health")
def health() -> dict:
    """Quick check that the app is running. Never returns personal data."""
    return {
        "status": "ok",
        "app": "Kinsum",
        "version": __version__,
        "ai_enabled": settings.ai_enabled,
        "data_dir_ready": settings.data_dir.exists(),
    }


# ---- Frontend (built React app) -------------------------------------------
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    """Serve files from frontend/dist, falling back to index.html for app routes."""
    if path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    candidate = (FRONTEND_DIST / path).resolve()
    if path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
        return FileResponse(candidate)
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {"detail": "Frontend not built yet. Run setup.bat (or: cd frontend && npm run build)."},
        status_code=503,
    )


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.kinsum_port)


if __name__ == "__main__":
    run()
