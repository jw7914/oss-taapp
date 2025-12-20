# Task Client Adapter

Adapter that wraps the auto-generated task service client to implement the `task_client_api.Client` protocol. Provides a seamless interface for task operations whether running locally (library) or remotely (service).

## Purpose

- Wrap the auto-generated `task_client_service_client` service client
- Implement the `task_client_api.Client` protocol for service-based task operations
- Translate between service response models and the expected `Task` and `TaskList` interfaces
- Enable dependency injection for service-based implementations

## Architecture

The package exposes a `ServiceClientAdapter` class that implements the `task_client_api.Client` interface by wrapping the auto-generated `Client` from `task_client_service_client`. It translates method calls to appropriate service endpoints and converts response models to the expected `Task` and `TaskList` interfaces.

## API Reference

### ServiceClientAdapter Class

Implements `task_client_api.Client` with the following methods:

**Tasklists:**

- `list_tasklists() -> list[TaskList]`: List all tasklists
- `insert_tasklist(tasklist: TaskList) -> TaskList`: Create a new tasklist
- `delete_tasklist(tasklist_id: str) -> bool`: Delete a tasklist

**Tasks:**

- `list_tasks(tasklist_id: str) -> list[Task]`: List tasks in a tasklist
- `get_task(tasklist_id: str, task_id: str) -> Task`: Get a specific task
- `insert_task(tasklist_id: str, task: Task) -> Task`: Create a new task
- `delete_task(tasklist_id: str, task_id: str) -> bool`: Delete a task

## Usage

```python
from task_client_service_client import Client as ServiceClient
from task_client_adapter import ServiceClientAdapter

# Create authenticated service client
service_client = ServiceClient(base_url="https://127.0.0.1:8001", token="your-token")

# Create adapter
adapter = ServiceClientAdapter(service_client)

# Use as task_client_api.Client
tasklists = adapter.list_tasklists()
tasks = adapter.list_tasks(tasklist_id="tasklist_123")
```

## Swagger UI Authentication

When using the Swagger UI documentation interface (available at `http://127.0.0.1:8001/docs`), the service automatically initiates the OAuth login flow when you attempt to hit an endpoint while not authenticated.

**Automatic OAuth Flow:**

1. Navigate to Swagger UI at `http://127.0.0.1:8001/docs`
2. Try to execute any endpoint (e.g., `GET /tasklists`) without being authenticated
3. The service detects missing credentials and automatically triggers the OAuth authentication flow
4. Your browser will open to Google's authorization page
5. Complete the OAuth flow in your browser
6. Once authenticated, return to Swagger UI and retry the endpoint

This automatic authentication eliminates the need to manually visit `/auth/login` before using the Swagger UI. The service dependency injection system handles credential detection and OAuth initiation transparently.

**Note:** Ensure `credentials.json` is present in the project root for the OAuth flow to work.

## Testing

```bash
uv run pytest src/task_client_adapter/tests/
```

## Implementation Details

The adapter implements the `task_client_api.Client` interface by:

1. **Wrapping the auto-generated client**: Uses `Client` from `task_client_service_client`
2. **Translating method calls**: Maps interface methods to appropriate service endpoints
3. **Converting response models**: Transforms service responses to `Task` and `TaskList` interfaces
4. **Dependency injection**: Auto-registers implementations via `register()` function

This allows the same interface to work whether the task client runs as a library (direct Google Tasks API calls) or as a service (network calls to the task service).
