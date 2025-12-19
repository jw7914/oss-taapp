"""FastAPI service for task client operations."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import gtask_client_impl  # noqa: F401
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from task_client_api import get_client as _get_client

from task_client_service.routers import auth_router, task_router, tasklist_router

# Make get_client available for monkeypatching in tests
get_client = _get_client

# Find project root (where .env file is located)
# This file is at: src/task_client_service/src/task_client_service/fast_api_service.py
# Project root is 4 levels up
_project_root = Path(__file__).parent.parent.parent.parent.parent
_env_file = _project_root / ".env"
load_dotenv(_env_file)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan."""
    logger.info("Starting Task Client Service...")
    logger.info("Task client will be initialized when first route is accessed")
    try:
        # Try to initialize the client during startup
        # If it fails (e.g., no credentials), set task_client to None
        # The client will be initialized lazily when routes are accessed
        try:
            # Use module-level get_client so tests can monkeypatch it
            client = get_client(interactive=False)
            app.state.task_client = client
            logger.info("Task client initialized successfully during startup")
        except RuntimeError as e:
            # If credentials aren't available, that's okay - client will be initialized lazily
            logger.info(
                "Task client not initialized during startup (will be initialized lazily): %s", e
            )
            app.state.task_client = None
        yield
    except (RuntimeError, OSError, ValueError) as e:
        logger.critical("Failed to start Task Client Service: %s", e, exc_info=True)
        raise
    finally:
        logger.info("Shutting down Task Client Service...")


app = FastAPI(
    title="Task Client Service",
    description="REST API for task client operations.",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY") or "dev-secret-key",
)

# Include routers
app.include_router(auth_router)
app.include_router(tasklist_router)
app.include_router(task_router)
