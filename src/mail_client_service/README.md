# Mail Client Service

A FastAPI-based Gmail client service that provides HTTP endpoints for Gmail authentication and message management operations.

## Overview

The Mail Client Service is a REST API wrapper around the Gmail client implementation, providing a web interface for managing Gmail messages. It offers secure authentication and comprehensive message operations through clean HTTP endpoints.

## Features

- **Gmail Authentication**: OAuth2-based Gmail account authentication with interactive login flow
- **Message Listing**: Retrieve multiple messages with configurable limits
- **Message Details**: Get full details of individual messages by ID
- **Mark as Read**: Mark specific messages as read
- **Message Deletion**: Delete messages from Gmail account
- **Error Handling**: Comprehensive error responses with detailed status information
- **State Management**: Persistent authentication state during application lifecycle

## API Endpoints

### Authentication

- `GET /login` - Authenticate Gmail account with OAuth2 flow
  - Supports `interactive` query parameter:
    - `GET /login?interactive=true` - Initiate interactive browser-based authentication
- `GET /logout` - Revoke authentication and log out the current Gmail account

### Messages

- `GET /messages` - List messages (supports `max_results` query parameter, 1-100, default: 3)
- `GET /messages/{id}` - Get detailed information for a specific message
- `POST /messages/{id}/mark-as-read` - Mark a message as read
- `DELETE /messages/{id}` - Delete a message

### General

- `GET /` - Welcome message and service status

## Installation

### Prerequisites

- Python 3.11 or higher
- Gmail API credentials (`credentials.json`)

### Setup

1. Install the package and its dependencies:

```bash
uv sync --all-packages --extra dev
```

2. Set up Gmail API credentials:
   - Place your `credentials.json` file in the project root

## Usage

### Starting the Service

```bash
# Activate virtual environment (.venv)
source .venv/bin/activate

# Start the FastAPI server from root of project
fastapi dev src/mail_client_service/src/mail_client_service/main.py

# Or with uvicorn
cd src/mail_client_service/src
uvicorn mail_client_service.main:app --reload --host 127.0.0.1 --port 8000
```

The service will be available at `http://localhost:8000` with interactive API documentation at `http://localhost:8000/docs`.

### Authentication Flow

1. Start the service
2. Call `GET /login` to initiate Gmail authentication (the service will use Gmail auth variables from your `.env` file by default).
   - To use the interactive login flow, call `GET /login?interactive=true`.
3. Follow the interactive OAuth2 flow in your browser (if applicable).
4. Once authenticated, use the other endpoints to manage messages.

### Example API Calls

> **Tip:**  
> You can explore and test all API endpoints interactively using the built-in UI at [http://localhost:8000/docs](http://localhost:8000/docs).  
> This interface allows you to authenticate, send requests, and view responses directly from your browser without writing any code.

```bash
# Authenticate
curl http://localhost:8000/login

# Get messages (default 3)
curl http://localhost:8000/messages

# Get messages with custom limit
curl "http://localhost:8000/messages?max_results=10"

# Get specific message
curl http://localhost:8000/messages/{message_id}

# Mark message as read
curl -X POST http://localhost:8000/messages/{message_id}/mark-as-read

# Delete message
curl -X DELETE http://localhost:8000/messages/{message_id}
```

## Response Format

All endpoints return JSON responses with a consistent structure:

### Success Response

```json
{
  "status": "success",
  "message": "Operation successful",
  "data": {
    /* endpoint-specific data */
  }
}
```

### Error Response

```json
{
  "error": "Error type",
  "message": "Detailed error description",
  "status": "error"
}
```

## Error Handling

The service provides detailed error responses for various scenarios:

- **401 Unauthorized**: User not authenticated
- **400 Bad Request**: Invalid message ID format
- **404 Not Found**: Message not found or missing credentials
- **403 Forbidden**: Access denied to Gmail resource
- **422 Unprocessable Entity**: Invalid query parameters
- **429 Too Many Requests**: Authentication already in progress
- **500 Internal Server Error**: Unexpected errors

## Dependencies

- **FastAPI**: Modern web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **mail-client-api**: Abstract mail client interface (workspace dependency)
- **gmail-client-impl**: Gmail-specific client implementation (workspace dependency)

### Project Structure

```
mail_client_service/
├── src/
│   └── mail_client_service/
│       └── main.py          # FastAPI application and endpoints
├── tests/                   # Test files
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

### Testing

There are two focused test files for the Mail Client Service. They live under
`src/mail_client_service/tests` and test different layers of the code:

- `test_client_contract.py` — unit/contract tests that verify the `Client` and
  `Message` shapes using simple mocks. This test validates that client implementations conform to the required interface.

- `test_api_endpoints_integration.py` — integration tests checks the
  FastAPI application using `fastapi.testclient.TestClient`. These tests cover
  routing, serialization, input validation and error mapping. This test validates the HTTP surface of the service.

Running the tests

- Run the unit (contract) tests only:

```bash
PYTHONPATH=src/mail_client_service/src:src/mail_client_api/src \
  pytest -q src/mail_client_service/tests/test_client_contract.py
```

- Run the integration (API) tests only:

```bash
PYTHONPATH=src/mail_client_service/src:src/mail_client_api/src \
  pytest -q src/mail_client_service/tests/test_api_endpoints_integration.py
```

- Run both test files for the mail_client_service package:

```bash
PYTHONPATH=src/mail_client_service/src:src/mail_client_api/src \
  pytest -q src/mail_client_service/tests
```
