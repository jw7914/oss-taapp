# Mail Client Service

A FastAPI-based REST API service that provides HTTP endpoints for mail operations using the existing mail client components.

## Overview

This service acts as a thin wrapper around the existing `gmail_client_impl` and `gmail_message_impl` components, exposing their functionality via RESTful HTTP endpoints.

## Features

- **RESTful API**: Clean HTTP endpoints for mail operations
- **Automatic Documentation**: Interactive API docs via FastAPI
- **Dependency Injection**: Uses FastAPI's dependency system for client management
- **Error Handling**: Comprehensive error responses with proper HTTP status codes
- **Type Safety**: Full Pydantic model validation for requests and responses

## API Endpoints

### Health & Status

- `GET /` - Service information and status
- `GET /health` - Health check endpoint

### Messages

- `GET /messages` - Get a list of message summaries
  - Query param: `max_results` (1-100, default: 10)
- `GET /messages/{message_id}` - Get full details of a specific message
- `POST /messages/{message_id}/mark-read` - Mark a message as read
- `DELETE /messages/{message_id}` - Delete a message
- `GET /messages/{message_id}/exists` - Check if a message exists

## Quick Start

### 1. Install Dependencies

From the workspace root:

```bash
uv sync --extra dev
```

### 2. Run the Service

```bash
# Option 1: Using the server script
cd src/mail_client_service/src
python -m mail_client_service.server

# Option 2: Using uvicorn directly
cd src/mail_client_service/src
uvicorn mail_client_service.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Access the API

- **Service**: http://127.0.0.1:8000
- **Interactive Docs**: http://127.0.0.1:8000/docs
- **OpenAPI Schema**: http://127.0.0.1:8000/openapi.json

## Example Usage

### Get Messages

```bash
curl "http://127.0.0.1:8000/messages?max_results=5"
```

### Get Specific Message

```bash
curl "http://127.0.0.1:8000/messages/{message_id}"
```

### Mark Message as Read

```bash
curl -X POST "http://127.0.0.1:8000/messages/{message_id}/mark-read"
```

### Delete Message

```bash
curl -X DELETE "http://127.0.0.1:8000/messages/{message_id}"
```

## Response Models

### MessageSummary

```json
{
  "id": "string",
  "subject": "string",
  "from_": "string",
  "date": "string",
  "snippet": "string"
}
```

### MessageDetail

```json
{
  "id": "string",
  "subject": "string",
  "from_": "string",
  "date": "string",
  "body": "string"
}
```

### OperationResponse

```json
{
  "success": true,
  "message": "string",
  "message_id": "string"
}
```

## Architecture

The service follows these principles:

1. **Thin Wrapper**: No business logic reimplementation - delegates to existing components
2. **Dependency Injection**: Uses FastAPI's `Depends()` for clean client management
3. **Lifecycle Management**: Proper startup/shutdown handling for the mail client
4. **Error Boundaries**: Comprehensive exception handling with appropriate HTTP status codes

## Testing

Run the tests:

```bash
cd src/mail_client_service
pytest tests/
```

## Dependencies

This service depends on the following workspace components:

- `mail-client-api` - Protocol definitions and factory functions
- `gmail-client-impl` - Gmail-specific implementation
- `gmail-message-impl` - Message object implementation

External dependencies:

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation and serialization
