# Task Client API

## Overview

`task_client_api` defines the abstract `Client` base class that every task client must implement. The package provides the abstraction, factory hooks, and no concrete logic.

## Purpose

This package serves as the contract for task client implementations:

- **API Contract**: Defines all task and tasklist operations through abstract base classes
- **Factory Pattern**: Provides `get_client()` factory that implementations override
- **Type Safety**: Exposes `Task` and `TaskList` abstractions for type checking

## Architecture

### Dependency Injection

Implementation packages replace the factory at import time:

```python
import gtask_client_impl  # rebinds task_client_api.get_client

from task_client_api import get_client
client = get_client(interactive=False)
```

## API Reference

### Client Abstract Base Class

Implements task and tasklist operations.

#### TaskList Operations

- `list_tasklists() -> list[TaskList]`: Lists all tasklists
- `insert_tasklist(tasklist: TaskList) -> TaskList`: Creates a new tasklist
- `delete_tasklist(tasklist: TaskList) -> bool`: Deletes a tasklist

#### Task Operations

- `list_tasks(tasklist: TaskList) -> list[Task]`: Lists all tasks in a tasklist
- `get_task(task_id: str) -> Task`: Retrieves a task by ID
- `insert_task(tasklist: TaskList, task: Task, parent: str = None, previous: str = None) -> Task`: Creates a new task
- `delete_task(task_id: str) -> bool`: Deletes a task

### Factory Functions

- `get_client(*, interactive: bool = False) -> Client`: Returns the bound implementation or raises `NotImplementedError` if none registered
- `get_task(task_id: str, raw_data: str) -> Task`: Creates a Task instance from raw data
- `get_tasklist(task_list_id: str, raw_data: str) -> TaskList`: Creates a TaskList instance from raw data

### Task Abstraction

```python
class Task(ABC):
    @property
    def id(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def notes(self) -> str | None: ...
    @property
    def status(self) -> str: ...
    @property
    def due(self) -> str | None: ...
    @property
    def completed(self) -> str | None: ...
    @property
    def deleted(self) -> bool: ...
    @property
    def hidden(self) -> bool: ...
    @property
    def parent(self) -> str | None: ...
    @property
    def position(self) -> str | None: ...
    @property
    def links(self) -> list[dict[str, str]]: ...
    @property
    def web_view_link(self) -> str | None: ...
    @property
    def assignment_info(self) -> dict[str, Any] | None: ...
```

### TaskList Abstraction

```python
class TaskList(ABC):
    @property
    def id(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def etag(self) -> str: ...
    @property
    def updated(self) -> str: ...
    @property
    def self_link(self) -> str: ...
```

## Usage Examples

### Basic Operations

```python
import gtask_client_impl
from task_client_api import get_client

client = get_client(interactive=False)
tasklists = client.list_tasklists()
for tasklist in tasklists:
    tasks = client.list_tasks(tasklist)
    for task in tasks:
        print(f"{task.title} ({task.status})")
```

### Task Management

```python
import gtask_client_impl
from task_client_api import get_client

client = get_client()
tasklist = client.list_tasklists()[0]

# Create a task
new_task = client.insert_task(tasklist, task_data)

# Delete a task
client.delete_task(new_task.id)
```

## Implementation Checklist

1. Implement every method in the `Client` abstract base class
2. Return objects compatible with `Task` and `TaskList` abstractions
3. Publish a factory (`get_client_impl`) and assign it to `task_client_api.get_client`
4. Honor the `interactive` flag (prompting only when `True`)
5. Handle task hierarchy (parent-child relationships)
6. Support task positioning and ordering within tasklists

## Testing

```bash
uv run pytest src/task_client_api/tests/ -q
uv run pytest src/task_client_api/tests/ --cov=src/task_client_api --cov-report=term-missing
```
