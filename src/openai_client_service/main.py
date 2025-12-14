"""Convenience module exposing the FastAPI app for tests and scripts."""

from .src.openai_client_service import main as _main
from .src.openai_client_service import routes as _routes

app = _main.app
routes = _routes

__all__ = ["app", "routes"]
