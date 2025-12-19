# Task Client Service

FastAPI service providing a REST API for Google Tasks operations via `task-client-api` and `gtask-client-impl`.

## Prerequisites

- Python 3.11+
- `uv` package manager
- `credentials.json` file for OAuth authentication

## Endpoints

### Authentication

- `GET /auth/login` - Initiate OAuth 2.0 login flow
- `GET /auth/callback` - OAuth callback handler
- `POST /auth/refresh` - Refresh access token
- `GET /auth/health-check` - Health check endpoint

### Tasklists

- `GET /tasklists` - List all tasklists
- `POST /tasklists` - Create a new tasklist
- `DELETE /tasklists/{tasklist_id}` - Delete a tasklist

### Tasks

- `GET /tasks/{tasklist_id}` - List tasks in a tasklist
- `GET /tasks/{tasklist_id}/{task_id}` - Get a specific task
- `POST /tasks/{tasklist_id}` - Create a new task
- `DELETE /tasks/{tasklist_id}/{task_id}` - Delete a task

## Running the Service

1. Install dependencies:

   ```bash
   uv sync --all-packages --extra dev
   ```

2. Start the service:

   ```bash
   uvicorn task_client_service.fast_api_service:app --reload --port 8001
   ```

3. Authenticate:

   - Visit `http://127.0.0.1:8001/auth/login` to initiate OAuth flow
   - Complete authentication in your browser

4. Access API documentation:
   - Swagger UI: `http://127.0.0.1:8001/docs`

## Swagger UI Authentication

When using the Swagger UI documentation interface, the service automatically initiates the OAuth login flow when you attempt to hit an endpoint while not authenticated.

**Automatic OAuth Flow:**

1. Navigate to Swagger UI at `http://127.0.0.1:8001/docs`
2. Try to execute any endpoint (e.g., `GET /tasklists`) without being authenticated
3. The service detects missing credentials and automatically triggers the OAuth authentication flow
4. Your browser will open to Google's authorization page
5. Complete the OAuth flow in your browser
6. Once authenticated, return to Swagger UI and retry the endpoint

This automatic authentication eliminates the need to manually visit `/auth/login` before using the Swagger UI. The service dependency injection system handles credential detection and OAuth initiation transparently.

**Note:** Ensure `credentials.json` is present in the project root for the OAuth flow to work.

## Example Usage

```bash
# Authenticate first
curl http://127.0.0.1:8001/auth/login

# List tasklists
curl http://127.0.0.1:8001/tasklists

# Create tasklist
curl -X POST http://127.0.0.1:8001/tasklists \
  -H "Content-Type: application/json" \
  -d '{"title": "My Task List"}'

# Create task
curl -X POST http://127.0.0.1:8001/tasks/tasklist_id \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Task",
    "status": "needsAction",
    "due": "2025-11-15T00:00:00.000Z"
  }'
```

## Testing

```bash
uv sync --extra test
uv run pytest
```

## HTTP Status Codes

- `200 OK` - Success
- `400 Bad Request` - Invalid request or attempting to delete default tasklist
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Resource not found
- `409 Conflict` - Tasklist title already exists
- `500 Internal Server Error` - Server error
