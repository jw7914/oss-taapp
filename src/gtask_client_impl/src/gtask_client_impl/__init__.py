"""Public exports for the Google Tasks client implementation package."""

import task_client_api

from gtask_client_impl.gtask_impl import (
    GTaskClient as _GTaskClient,
)
from gtask_client_impl.gtask_impl import (
    get_client_impl as get_client_impl,
)
from gtask_client_impl.gtask_impl import (
    register as _register_client,
)
from gtask_client_impl.task_impl import (
    GTask as _GTask,
)
from gtask_client_impl.task_impl import (
    get_task_impl as get_task_impl,
)
from gtask_client_impl.task_impl import (
    register as _register_task,
)
from gtask_client_impl.tasklist_impl import (
    GTaskList as _GTaskList,
)
from gtask_client_impl.tasklist_impl import (
    get_tasklist_impl as get_tasklist_impl,
)
from gtask_client_impl.tasklist_impl import (
    register as _register_tasklist,
)

# Explicit re-exports for type checking
GTaskClient: type[task_client_api.Client] = _GTaskClient
GTask: type[task_client_api.task.Task] = _GTask
GTaskList: type[task_client_api.tasklist.TaskList] = _GTaskList


def register() -> None:
    """Register the Google Tasks client, task, and tasklist implementations."""
    _register_client()
    _register_task()
    _register_tasklist()


# Dependency Injection happens at import time
register()
