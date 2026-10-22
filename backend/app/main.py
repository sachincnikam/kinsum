"""Kinsum local server.

Serves the API under /api and the built frontend (frontend/dist) for everything else.
It listens on 127.0.0.1 only, so no other device on the network can connect.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .config import REPO_ROOT, settings
from .lock import LockManager, LockMiddleware
from .lock import router as lock_router

FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

# Requests must name this computer, which stops other websites reaching the app
# through a look-alike address (DNS rebinding).
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


def create_app(data_dir: Path | None = None, idle_lock_minutes: int | None = None) -> FastAPI:
    manager = LockManager(
        data_dir or settings.data_dir,
        idle_lock_minutes if idle_lock_minutes is not None else settings.kinsum_idle_lock_minutes,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def idle_watch():
            while True:
                await asyncio.sleep(15)
                manager.check_idle()

        task = asyncio.create_task(idle_watch())
        try:
            yield
        finally:
            task.cancel()
            manager.lock()  # quitting the app forgets the key and closes the database

    app = FastAPI(title="Kinsum", version=__version__, lifespan=lifespan)
    app.state.lock = manager
    app.add_middleware(LockMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    app.include_router(lock_router)

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

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.kinsum_port)


if __name__ == "__main__":
    run()
