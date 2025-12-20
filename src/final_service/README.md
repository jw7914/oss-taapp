# Final Service - Discord + AI + Google Tasks Integration

A unified FastAPI service that integrates Discord chat, OpenAI-powered responses, and Google Tasks management into an intelligent task automation platform.

## 🎯 Overview

This service allows users to interact with a Discord bot that:

- Provides AI-powered responses using OpenAI GPT-4o-mini
- Automatically creates, closes, and deletes tasks in Google Tasks
- Determines user intent through intelligent keyword detection
- Processes messages asynchronously for optimal performance

## 🏗️ Architecture

### Components

1. **Discord Gateway** - Real-time WebSocket connection for message listening
2. **OpenAI Client** - AI-powered response generation
3. **Google Tasks Client** - Task management via OAuth2
4. **FastAPI Server** - REST API for service management

### Message Flow

```
Discord Message (@bot mention)
    ↓
Gateway Listener (WebSocket)
    ↓
Async Message Processor
    ↓
AI Response Generation (OpenAI)
    ↓
Intent Classification (Keywords)
    ↓
Task Action (Create/Close/Delete) or AI Response
```

## 🚀 Features

### Intent Detection

The service uses keyword-based classification:

- **Create**: `create`, `add`, `new task`, `need to`, `want to`, `remember`, `remind`, `should`, `have to`
- **Close**: `done`, `finish`, `complete`, `resolved`, `fixed`, `close`, `mark as done`
- **Delete**: `delete`, `remove`, `forget`, `cancel`, `discard`

### Task Management

- **Create**: Automatically creates tasks with Discord message as title and AI analysis as description
- **Close**: Marks matching tasks as completed in Google Tasks
- **Delete**: Removes tasks from Google Tasks
- **Search**: Smart query cleaning (removes mentions and command keywords)

## 📦 Installation

### Prerequisites

- Python 3.11+
- Discord Bot Token and Application credentials
- OpenAI API Key
- Google Tasks OAuth credentials

### Setup

1. **Install dependencies**:

   ```bash
   cd src/final_service
   uv sync
   ```

2. **Configure environment variables**:

   ```bash
   # Discord
   DISCORD_CLIENT_ID=your_client_id
   DISCORD_CLIENT_SECRET=your_client_secret
   DISCORD_BOT_TOKEN=your_bot_token

   # OpenAI
   OPENAPI_KEY=your_openai_key

   # Google Tasks
   TASKS_CLIENT_ID=your_google_client_id
   TASKS_CLIENT_SECRET=your_google_client_secret
   TASKS_REFRESH_TOKEN=your_refresh_token
   ```

3. **Run the service**:
   ```bash
   uv run uvicorn src.final_service.main:app --reload --port 8000
   ```

## 🎮 Usage

### Discord Commands

#### Create a Task

```
@bot I need to buy pens for school
```

**Response**: `✓ Task has been created for this issue.`

#### Close a Task

```
@bot I'm done with the homework
```

**Response**: `✓ Task has been marked as completed.`

#### Delete a Task

```
@bot delete the pens task
```

**Response**: `✓ Task has been deleted.`

#### General Chat

```
@bot What's the weather like?
```

**Response**: [AI-generated response]

### API Endpoints

| Endpoint         | Method | Description                         |
| ---------------- | ------ | ----------------------------------- |
| `/`              | GET    | Health check                        |
| `/login`         | GET    | Discord OAuth login                 |
| `/auth/callback` | GET    | OAuth callback                      |
| `/user`          | GET    | Get current Discord user            |
| `/tasklists`     | GET    | List Google Task lists              |
| `/tasks`         | GET    | List tasks (requires `tasklist_id`) |
| `/health`        | GET    | Service health status               |
| `/metrics`       | GET    | Prometheus metrics                  |

## 🔧 Configuration

### Dependencies

```toml
[project]
dependencies = [
    "fastapi[standard]>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "discord-client-impl",
    "openai-client-impl",
    "tickets-client-impl",
    "gtask-client-impl",
    "prometheus-fastapi-instrumentator>=6.1.0",
]
```

### Workspace Sources

The service uses workspace dependencies:

- `discord-client-impl` - Discord WebSocket and API client
- `openai-client-impl` - OpenAI GPT integration
- `tickets-client-impl` - Google Tasks wrapper
- `gtask-client-impl` - Google Tasks API client

## 🧪 Testing

Run tests:

```bash
uv run pytest tests/ -v
```

Check code quality:

```bash
uv run ruff check .
uv run ruff format .
```

## 📊 Monitoring

### Logging

The service provides comprehensive logging with prefixes:

- `[ASYNC]` - Async message processing
- `[INTENT]` - Intent classification
- `[CREATE-TASK]` - Task creation
- `[CLOSE-TASK]` - Task closure
- `[DELETE-TASK]` - Task deletion
- `[CREATE-TASK-SYNC]` - Synchronous task operations
- `[CLOSE-TASK-SYNC]` - Synchronous closure operations
- `[DELETE-TASK-SYNC]` - Synchronous deletion operations

### Metrics

Prometheus metrics are exposed at `/metrics` for monitoring:

- Request counts
- Response times
- Error rates

## 🔐 Authentication

### Discord OAuth Flow

1. User visits `/login`
2. Redirected to Discord authorization
3. User grants permissions
4. Callback to `/auth/callback` with code
5. Service exchanges code for access token
6. Token stored in cookie for session

### Google Tasks OAuth

The service uses OAuth2 with refresh tokens for non-interactive access:

- Client credentials from Google Cloud Console
- Refresh token obtained via interactive flow
- Automatic token refresh when expired

## 🏃 Development

### Project Structure

```
src/final_service/
├── src/
│   └── final_service/
│       └── main.py          # Main service implementation
├── tests/                    # Test files
├── pyproject.toml           # Package configuration
└── README.md                # This file
```

### Key Functions

- `listen_for_messages()` - Discord gateway WebSocket listener
- `process_message_async()` - Async message processing pipeline
- `_determine_task_intent_async()` - Keyword-based intent classifier
- `_handle_ticket_creation_async()` - Creates tasks in Google Tasks
- `_handle_ticket_closure_async()` - Marks tasks as completed
- `_handle_task_deletion_async()` - Deletes tasks

## 🚦 Error Handling

The service gracefully handles errors:

- Missing credentials → User-friendly error messages
- API failures → Fallback responses
- Invalid queries → No matching task notifications
- Network issues → Retry with exponential backoff

## 🔄 Future Enhancements

- [ ] Task priority and due date support
- [ ] Multi-tasklist management
- [ ] Advanced task search filters
- [ ] Batch task operations
- [ ] Task update/edit commands
- [ ] Natural language date parsing
- [ ] Task assignment to other users

## 📚 Related Documentation

- [Discord Client Implementation](../discord_client_impl/)
- [OpenAI Client Implementation](../openai_client_impl/)
- [Google Tasks Client](../gtask_client_impl/)
- [Tickets API](../tickets_api/)

## 📄 License

See the root repository LICENSE file.
