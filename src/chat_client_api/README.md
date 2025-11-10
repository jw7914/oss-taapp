# chat_client_api — Chat client contract

## Overview

`chat_client_api` provides the abstract contracts (interfaces) that chat client implementations must satisfy. It contains:

- The `ChatClient` abstract base class (core operations).
- Message and channel contracts in `chat_client_api.message`.
- A placeholder factory function `get_client(*, interactive: bool = False)` that implementations rebind at import time.

This package contains only interfaces and documentation; concrete behavior is implemented in separate packages (for example `discord_client_impl`).

## Quick start

Use the published factory to obtain a client instance from an implementation that has been imported into the runtime:

```python
import discord_client_impl  # binds an implementation to chat_client_api.get_client

from chat_client_api import get_client

client = get_client()
for msg in client.get_messages(channel_id="general", max_results=5):
		print(msg.message_id, msg.author_username, msg.content)
```

## API reference

ChatClient (core contract)

Implementations must provide a `ChatClient` that exposes the following methods (signatures from `src/chat_client_api/src/chat_client_api/client.py`):

- `get_message(channel_id: str, message_id: str) -> ChatMessage`
  - Return a single message by id.
- `delete_message(channel_id: str, message_id: str) -> bool`
  - Delete a message. Return True on success, False on failure.
- `get_messages(channel_id: str, max_results: int = 10) -> Iterator[ChatMessage]`
  - Lazily yield up to `max_results` messages from the specified channel.

Factory

- `get_client(*, interactive: bool = False) -> ChatClient` — placeholder exported by this package. Implementations should publish their own factory (for example `get_client_impl`) and assign it to `chat_client_api.get_client` when imported. If no implementation is bound, calling the factory raises `NotImplementedError`.

## Message and channel contracts

`ChatMessage` (from `chat_client_api.message`) exposes these properties that implementations must provide:

- `message_id: str`
- `author: str`
- `author_username: str`
- `channel_id: str`
- `timestamp: str` (ISO 8601 or consistent human-readable form)
- `content: str`

`ChatChannel` exposes:

- `channel_id: str`
- `channel_name: str`
- `channel_type: int` (implementation-defined enumeration)
- `channel_position: int`

## Usage examples

Note: this package only exposes the contract. Before calling `get_client()` you must import an implementation so the factory is bound, otherwise `get_client()` raises `NotImplementedError`.

Iterate messages from a channel:

```python
import discord_client_impl  # ensure an implementation binds chat_client_api.get_client
from chat_client_api import get_client

try:
	client = get_client()
except NotImplementedError:
	raise RuntimeError(
		"No chat client implementation installed. Import an implementation (e.g. discord_client_impl) before calling get_client()."
	)

for msg in client.get_messages(channel_id="C123456", max_results=3):
	print(f"{msg.message_id} [{msg.author_username}]: {msg.content}")
```

Get and delete a single message:

```python
import discord_client_impl
from chat_client_api import get_client

client = get_client()
msg = client.get_message(channel_id="C123456", message_id="M7890")
print(msg.content)
deleted = client.delete_message(channel_id=msg.channel_id, message_id=msg.message_id)
print("deleted:", deleted)
```

## Implementation checklist

1. Implement every abstract method in `ChatClient`.
2. Return objects compatible with `chat_client_api.message.ChatMessage` and `ChatChannel`.
3. Publish a factory (e.g. `get_client_impl`) and assign it to `chat_client_api.get_client` on import.
4. Honour the `interactive` flag: only prompt the user when `interactive=True`.

## Testing

Run the package tests from the repository root:

```bash
pytest src/chat_client_api/tests/ -q
pytest src/chat_client_api/tests/ --cov=src/chat_client_api --cov-report=term-missing
```

## Contributing

When adding an implementation:

- Keep the implementation in a separate package (for example `discord_client_impl`).
- Rebind the factory by assigning the implementation factory to `chat_client_api.get_client` during import.
- Add tests under `src/<implementation>/tests/` that validate the contract against the implementation.

## Notes

This package intentionally exposes interfaces only. Consumers should rely on the documented contracts and obtain real clients via implementations that bind the factory.
