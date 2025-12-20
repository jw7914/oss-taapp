"""Task client adapter package for wrapping auto-generated client."""

import task_client_api

from .service_client_adapter import (
    ServiceClientAdapter as _ServiceClientAdapter,
)
from .service_client_adapter import (
    register as _register_service_client,
)
from .service_task import (
    register as _register_service_task,
)
from .service_tasklist import (
    register as _register_service_tasklist,
)

# Explicit re-export for type checking
ServiceClientAdapter: type[task_client_api.Client] = _ServiceClientAdapter


def register() -> None:
    """Register the ServiceClientAdapter, ServiceTask, and ServiceTaskList implementations."""
    _register_service_client()
    _register_service_task()
    _register_service_tasklist()


# Dependency Injection happens at import time
register()
