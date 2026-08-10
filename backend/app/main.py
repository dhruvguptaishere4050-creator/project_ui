import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, Response

from app.config import get_settings
from app.database import Base, SessionLocal, apply_schema_updates, engine
from app.routers import academics, auth, insights, people
from app.seed import seed

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.validate_for_runtime()
    Base.metadata.create_all(bind=engine)
    apply_schema_updates(engine)
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed(db)
            db.commit()
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Centralised, role-based academic management for administrators, teachers, "
        "students and parents, with AI-generated performance insights."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(people.router)
app.include_router(academics.router)
app.include_router(insights.router)


def resolve_static_file(static_root: Path, full_path: str) -> Path:
    """Maps a request path to a bundle file, falling back to the SPA shell.

    Paths escaping the bundle (``../`` segments, absolute paths) never resolve to
    a file outside it.
    """
    index = static_root / "index.html"
    if not full_path:
        return index
    root = static_root.resolve()
    candidate = (root / full_path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return index
    return candidate


if settings.static_dir and Path(settings.static_dir).is_dir():
    static_root = Path(settings.static_dir)

    app.mount("/assets", StaticFiles(directory=static_root / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        return FileResponse(resolve_static_file(static_root, full_path))
