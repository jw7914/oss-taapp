# Google Tasks Client Implementation

## Overview

`gtask_client_impl` provides a concrete `task_client_api.Client` backed by the Google Tasks API. It handles OAuth2 authentication, makes Tasks API calls, and returns `GTask` and `GTaskList` objects.

## Purpose

This package serves as the production-ready Google Tasks integration:

- **Google Tasks API Integration**: Connects to Google Tasks using official Google APIs
- **OAuth2 Authentication**: Handles secure authentication with multiple modes (interactive/non-interactive)
- **ABC Implementation**: Provides concrete implementation of all Client operations
- **Dependency Injection**: Automatically registers itself as the Client implementation

## Architecture

### Authentication Modes

- `interactive=True`: Launches the browser OAuth flow and persists `token.json`. Use for local setup.
- `interactive=False`: Reads environment variables or existing tokens. Preferred for CI/CD and production.

Credential priority: environment variables → `token.json` → `credentials.json` (interactive fallback).

### Dependency Injection

```python
import gtask_client_impl  # rebinds the factory

from task_client_api import get_client
client = get_client(interactive=False)
```

## API Reference

### GTaskClient

Implements the `task_client_api.Client` abstract base class.

#### Tasklist Operations

- `list_tasklists() -> list[TaskList]`: Lists all tasklists.
- `insert_tasklist(tasklist: TaskList) -> TaskList`: Creates a new tasklist.
- `delete_tasklist(tasklist_id: str) -> bool`: Deletes a tasklist by ID.

#### Task Operations

- `list_tasks(tasklist_id: str) -> list[Task]`: Lists all tasks in a tasklist.
- `get_task(tasklist_id: str, task_id: str) -> Task`: Retrieves a specific task.
- `insert_task(tasklist_id: str, task: Task) -> Task`: Creates a new task.
- `delete_task(tasklist_id: str, task_id: str) -> bool`: Deletes a task.

### Factory Function

`get_client_impl(*, interactive: bool = False) -> task_client_api.Client`: Creates a `GTaskClient` and assigns it to `task_client_api.get_client` during import.

## Usage Examples

### Basic Operations

```python
import gtask_client_impl
from task_client_api import get_client

client = get_client(interactive=False)

# List tasklists
tasklists = client.list_tasklists()
for tasklist in tasklists:
    print(f"{tasklist.id}: {tasklist.title}")

# List tasks
tasks = client.list_tasks(tasklist_id="your_tasklist_id")
for task in tasks:
    print(f"{task.title} - {task.status}")
```

### Development Setup

```python
import gtask_client_impl
from task_client_api import get_client

client = get_client(interactive=True)  # opens browser on first run
tasklists = client.list_tasklists()
print(f"Found {len(tasklists)} tasklists")
```

### Task Management

```python
import gtask_client_impl
from task_client_api import get_client, task

client = get_client()

# Create a tasklist
new_tasklist = task.tasklist.get_tasklist(raw_data='{"title": "My Tasks"}')
created = client.insert_tasklist(new_tasklist)

# Create a task
new_task = task.task.get_task(raw_data='{"title": "Complete project", "status": "needsAction"}')
created_task = client.insert_task(created.id, new_task)

# Delete a task
client.delete_task(created.id, created_task.id)
```

## Authentication Setup

### Development Setup (Interactive)

1. **Google Cloud Console Setup**:

   - Create a project and enable Tasks API
   - Create OAuth2 credentials (Desktop application type)
   - Download `credentials.json`

2. **Local Development**:

   ```python
   import gtask_client_impl
   from task_client_api import get_client

   # First run - opens browser for consent
   client = get_client(interactive=True)
   ```

3. **Token Storage**:
   - OAuth2 tokens are saved to `token.json`
   - Subsequent runs use stored tokens
   - Tokens auto-refresh when expired

### Production Setup (Non-Interactive)

1. **Environment Variables**:

   ```bash
   export TASKS_CLIENT_ID="your_client_id"
   export TASKS_CLIENT_SECRET="your_client_secret"
   export TASKS_REFRESH_TOKEN="your_refresh_token"
   ```

2. **Production Usage**:

   ```python
   import gtask_client_impl
   from task_client_api import get_client

   # Uses environment variables
   client = get_client(interactive=False)
   ```

3. **CI/CD Integration**:
   - Set environment variables in CircleCI/GitHub Actions
   - No browser interaction required
   - Tokens refresh automatically

### Credential Sources (Priority Order)

1. **Environment Variables** (highest priority)

   - `TASKS_CLIENT_ID`, `TASKS_CLIENT_SECRET`, `TASKS_REFRESH_TOKEN`

2. **Local Token File**

   - `token.json` (created by interactive flow)

3. **Local Credentials File**
   - `credentials.json` (downloaded from Google Cloud Console)

## Testing

```bash
uv run pytest src/gtask_client_impl/tests/ -q
uv run pytest src/gtask_client_impl/tests/ --cov=src/gtask_client_impl --cov-report=term-missing
```

- Unit tests rely on mocks—no real Google Tasks calls.
- Integration and e2e suites in `tests/` expect credentials or environment variables.

## Google Tasks API Integration

### Scopes Required

The client requests these Google Tasks API scopes:

```python
SCOPES = [
    'https://www.googleapis.com/auth/tasks',  # Full access to tasks
]
```

### Response Handling

Google Tasks API responses are processed efficiently:

1. **List Operations**: Retrieves paginated lists of tasklists or tasks
2. **CRUD Operations**: Creates, reads, updates, and deletes tasks and tasklists
3. **JSON Conversion**: Converts API responses to GTask and GTaskList instances through dependency injection
