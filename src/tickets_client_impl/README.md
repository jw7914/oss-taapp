# Tickets Client Implementation

## Overview

`tickets_client_impl` provides a concrete implementation of `tickets_api.TicketInterface` using Google Tasks as the backend storage. It adapts ticket operations to task operations through `gtask_client_impl`.

## Purpose

This package serves as an adapter that maps ticket operations to Google Tasks:

- **Tickets API Implementation**: Implements `tickets_api.TicketInterface`
- **Google Tasks Backend**: Uses `gtask_client_impl` for all operations
- **Status Mapping**: Maps ticket statuses to task statuses and title prefixes
- **Default Tasklist**: Uses the first available tasklist for storage

## Architecture

### Status Mapping

Tickets map to Google Tasks as follows:

- **OPEN**: Task status `"needsAction"`, no prefix
- **IN_PROGRESS**: Task status `"needsAction"`, title prefixed with `"(IP) "`
- **CLOSED**: Task status `"completed"`, prefix removed

### Field Mappings

- `Ticket.id` → `Task.id`
- `Ticket.title` → `Task.title` (with `"(IP) "` prefix for IN_PROGRESS)
- `Ticket.description` → `Task.notes`
- `Ticket.status` → Derived from `Task.status` and title prefix
- `Ticket.assignee` → Always `None` (not supported by Google Tasks)

### Tasklist Strategy

- Uses the first tasklist from `list_tasklists()`
- Caches tasklist ID after first fetch
- All operations use the cached default tasklist

## Usage

```python
import gtask_client_impl  # noqa: F401
from tickets_api import TicketStatus
from tickets_client_impl import TicketsClient

# Create client
client = TicketsClient(interactive=False)

# Create ticket
ticket = client.create_ticket(
    title="Fix login bug",
    description="Users cannot authenticate"
)

# Get ticket
ticket = client.get_ticket(ticket_id)

# Search tickets
open_tickets = client.search_tickets(status=TicketStatus.OPEN)
bug_tickets = client.search_tickets(query="bug")

# Update ticket
updated = client.update_ticket(
    ticket_id,
    status=TicketStatus.IN_PROGRESS,
    title="Fix login bug (updated)"
)

# Delete ticket
success = client.delete_ticket(ticket_id)
```

## API Reference

### TicketsClient

Implements `tickets_api.TicketInterface`.

#### Methods

- `create_ticket(title: str, description: str, assignee: str | None = None) -> Ticket`: Creates a ticket with OPEN status.
- `get_ticket(ticket_id: str) -> Ticket | None`: Retrieves ticket by ID. Returns None if not found.
- `search_tickets(query: str | None = None, status: TicketStatus | None = None) -> list[Ticket]`: Searches default tasklist. Filters by query (title/description) and/or status.
- `update_ticket(ticket_id: str, status: TicketStatus | None = None, title: str | None = None) -> Ticket`: Updates status and/or title. Uses delete-and-recreate pattern (new task ID).
- `delete_ticket(ticket_id: str) -> bool`: Deletes ticket. Returns True if successful.

### Ticket

Implements `tickets_api.Ticket`.

#### Properties

- `id: str`: Unique identifier
- `title: str`: Title (prefix removed if present)
- `description: str`: Description
- `status: TicketStatus`: Status (OPEN, IN_PROGRESS, CLOSED)
- `assignee: str | None`: Always None

## Implementation Details

### Update Behavior

`update_ticket()` uses delete-and-recreate because Google Tasks has no update operation:

- Underlying task ID changes after update
- Ticket interface maintains original ID for caller
- All data preserved except internal task ID

### Search Implementation

- Searches only default tasklist
- Case-insensitive query matching
- Searches title and description
- Returns all matches (no limit)
- Can filter by status, query, or both

### Status Detection

Status determined by:

1. Task status `"completed"` → CLOSED
2. Title starts with `"(IP) "` → IN_PROGRESS
3. Otherwise → OPEN

## Dependencies

- `tickets-api`: Ticket abstractions
- `gtask-client-impl`: Google Tasks integration (workspace)
- `task-client-api`: Task abstractions (via gtask-client-impl)

## Testing

```bash
pytest tests/
```

Test coverage includes:

- Status mapping and prefix handling
- All TicketInterface methods
- Status detection edge cases
- Search filtering logic
- Update and delete operations

## Authentication

Uses `gtask_client_impl` authentication. See `gtask_client_impl` README for setup:

- **Development**: Set `interactive=True` for browser OAuth flow
- **Production**: Set environment variables (`TASKS_CLIENT_ID`, `TASKS_CLIENT_SECRET`, `TASKS_REFRESH_TOKEN`)
