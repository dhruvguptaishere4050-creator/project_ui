"""Entry point for ASGI servers: ``uvicorn main:app``."""

from app.main import app

__all__ = ["app"]
