# ServiceClientAdapter

**Adapter class** (`ServiceClientAdapter`) that interacts with the mail_client_api service.

## Features

- **Login**: Authenticate with the mail client service.
- **Get Message by ID**: Retrieve an individual message.
- **Delete Message**: Delete a specific message by its ID.
- **Mark as Read**: Mark a message as read.
- **Get Multiple Messages**: Retrieve a limited number of inbox messages.

---

## Code Overview

The `ServiceClientAdapter` extends the `mail_client_api.Client` class and acts as an interface to the API.

### Key Methods

- `login()`  
  Authenticates the user by calling the **authentication API**.

- `get_message(message_id: str)`  
  Retrieves a specific message using its ID.

- `delete_message(message_id: str)`  
  Deletes a message given its ID.

- `mark_as_read(message_id: str)`  
  Marks a message as read in the inbox.

- `get_messages(max_results: int = 10)`  
  Returns a limited number of messages from the inbox (default: 10).

---

## Example Usage

```
from service_client_adapter import ServiceClientAdapter

if __name__ == "__main__":
    adapter = ServiceClientAdapter()

    # Authenticate
    adapter.login()

    # Get top 3 inbox messages
    messages = adapter.get_messages(3)
    print(messages)

    # Get a single message by ID
    message = adapter.get_message("message_id_here")
    print(message)

    # Mark a message as read
    adapter.mark_as_read("message_id_here")

    # Delete a message
    adapter.delete_message("message_id_here")
```

## Updating the API Client

If the underlying mail_client_api schema changes, the API client code must be regenerated.  
This project relies on **openapi-python-client** to generate the `mail_client_service_api_client` package.

To regenerate:

```
uv add openapi-python-client
openapi-python-client generate --url http://127.0.0.1:8000/openapi.json
```

This will rebuild the client package from the updated OpenAPI specification, with the project structure similar to this:

```
mail-client-service-api-client/
│
├── mail_client_service_api_client/      # Main package
│   ├── api/                             # Auto-generated API endpoints
│   │   ├── __init__.py
│   │   └── *ENDPOINTS AS FOLDERS*      # Each folder/module for an endpoint group
│   ├── models/                          # Pydantic models for request/response bodies
│   ├── client.py                        # Base HTTP client wrapper
│   ├── errors.py                        # Error handling definitions
│   ├── types.py                         # Shared type helpers
│   ├── py.typed                         # Typing marker (for mypy/static checkers)
│   └── __init__.py                      # Package initializer
│
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## Notes

- By default, the client connects to `http://127.0.0.1:8000`.  
  You can update the base URL inside the `ServiceClientAdapter` constructor if your API server runs elsewhere.

- The adapter expects API endpoints defined in `mail_client_service_api_client.api` modules to be reachable.

## Test

To run the pytest:

```
pytest -v src/service_client_adapter/tests
```

To test for coverage:

```
pytest src/service_client_adapter/tests --cov=src/service_client_adapter --cov-report=term-missing -v

```
