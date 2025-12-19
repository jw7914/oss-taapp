"""FastAPI routers for the task client service."""

from fastapi import APIRouter

from .auth_router import router as _auth_router
from .task_router import router as _task_router
from .tasklist_router import router as _tasklist_router

# Explicit re-exports for type checking
auth_router: APIRouter = _auth_router
task_router: APIRouter = _task_router
tasklist_router: APIRouter = _tasklist_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(task_router)
router.include_router(tasklist_router)
