# Contributing Document

This guide explains the base repository. It is broken up in to sections that explains its architecture, interfaces, development workflow, testing conventions, and CI.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Repository Structure](#repository-structure)
3. [Testing Strategy](#testing-strategy)
4. [Development Tools](#development-tools)

## Architecture Overview

- Four primary components live under `src/`:
  - `mail_client_api` — the small, framework-like abstraction that defines contracts (interfaces) for working with mail messages and clients.
  - `gmail_client_impl` — a concrete implementation of the `mail_client_api` using the Gmail REST API.
  - `chat_client_api` - small abstraction that defines an interface for chat messages 
  - `discord_client_impl` - a concrete implementation of the `chat_client_api` using the Discord REST API
- The repository uses a `src` layout for packages to simplify installs and to make imports explicit.
- Components communicate via clean, small public interfaces (ABCs) rather than sharing implementation details.

### Components and interactions

- `mail_client_api` exposes the `Client` and `Message` abstractions (abstract base classes) and thin factory fallbacks like `get_client()` and `get_message()`.
- `gmail_client_impl` implements those abstractions (`GmailClient`, `GmailMessage`) and registers them into the API module at runtime using simple registration functions (dependency injection — see below).
- `chat_client_api` exposes the ChatClient and ChatMessage abstractions (ABCs) and factory methods like get_client() and get_message().
- `discord_client_impl` implements these abstractions (DiscordClient, DiscordMessage, DiscordChannel) and registers them at runtime using dependency injection.
- Tests exercise both the abstraction surface and the concrete implementation; integration and CI glue use environment variables or local token files to obtain credentials.

### Interface design

- Mail Client: `mail_client_api.client.Client` and `mail_client_api.message.Message` — both are ABCs that define the contract for mail operations and message properties.
- Chat Client: `chat_client_api.client.ChatClient` and `chat_client_api.message.ChatMessage` — ABCs defining chat operations and message properties.
- Additional Channel interface: `chat_client_api.channel.ChatChannel` — ABC for channel operations specific to chat platforms.
- Design rationale: use small, explicit interfaces (few methods/properties) to make mocking, testing, and alternate implementations easy. The ABCs are intentionally minimal and focused on the operations the remainder of the codebase needs.

### Implementation details

- The interfaces are implemented as Python Abstract Base Classes (ABCs) from `abc` in `src/mail_client_api/src/mail_client_api/client.py` and `message.py`.
- Concrete implementations are regular classes that inherit from the ABCs, e.g. `GmailClient(mail_client_api.Client)` and `GmailMessage(mail_client_api.message.Message)` in `src/gmail_client_impl/src/gmail_client_impl/`.
- The implementations use the `google-api-python-client` and `google-auth*` libraries to communicate with Gmail. The message parsing uses the standard library `email` package to decode RFC2047 and multipart messages.
- The interfaces are implemented as Python Abstract Base Classes (ABCs) from abc in `src/chat_client_api/src/chat_client_api/client.py`, message.py, and channel.py.
- Concrete implementations are regular classes that inherit from these ABCs, e.g. `DiscordClient(chat_client_api.Client)`, `DiscordMessage(chat_client_api.message.Message)`, and `DiscordChannel(chat_client_api.channel.Channel)` in `src/discord_client_impl/src/discord_client_impl/`.
- The implementation uses the authlib library for OAuth2 authentication and httpx for making REST API calls to the Discord API.
- Configuration for tokens and credentials is handled through environment variables.

### ABC vs typing.Protocol

- ABCs are nominal: a class must inherit from the ABC or be registered to be considered a subclass. They can provide enforced abstractmethods and runtime isinstance checks.
- `typing.Protocol` is structural: any object with the right attributes/methods satisfies the Protocol — no inheritance necessary. Protocols are lighter-weight for duck-typed designs and offer better test/mocking ergonomics when you only need structural compliance.
- In this repository, ABCs were chosen to make the contract explicit and to allow clear `isinstance`/`issubclass` checks during development and testing. Converting to `Protocol` would remove nominal coupling and could simplify some tests, but at the cost of losing an explicit type hierarchy.

Dependency injection (how an implementation is wired into the API)

- This project uses a tiny, explicit registration pattern: implementation modules expose a `register()` function which assigns concrete factories to the API module-level functions. That assignment is the injection point.

Example:

```py
# in src/gmail_client_impl/src/gmail_client_impl/gmail_impl.py  
def get_client_impl(*, interactive: bool = False) -> mail_client_api.Client:
    return GmailClient(interactive=interactive)

def register() -> None:
    # Inject the concrete implementation into the API module
    mail_client_api.get_client = get_client_impl
```

And for messages:

```py
# in src/gmail_client_impl/src/gmail_client_impl/message_impl.py
def get_message_impl(msg_id: str, raw_data: str) -> message.Message:
    return GmailMessage(msg_id=msg_id, raw_data=raw_data)

def register() -> None:
    # Inject the concrete message factory
    message.get_message = get_message_impl
    mail_client_api.get_message = get_message_impl
```

What this enables

- Tests and other components can swap the concrete implementation simply by calling the implementation's `register()` or by providing an alternative factory. This pattern keeps the API module as the single place the rest of the code depends on, making substitution, testing, and experimenting straightforward.

## Repository Structure

### Project Organization

Top-level files

- `pyproject.toml` — workspace root settings (uv workspace members, shared tool settings such as ruff, mypy, pytest defaults, coverage thresholds).
- `CONTRIBUTING.md`, `DESIGN.md`, `README.md`, and `docs/` — high-level documentation and learning material.

src/

- `src/mail_client_api/` — the API package. Contains an internal `pyproject.toml` that describes packaging for this component.
- `src/gmail_client_impl/` — concrete Gmail implementation. Also has its own `pyproject.toml` and tests.

tests/

- `tests/integration/` — integration tests that typically talk to external systems (run with real credentials or CI context).
- `tests/e2e/` — end-to-end tests that exercise the full application flow.

Why the `src` layout

- The `src` layout prevents accidental import of packages from the working directory while running tests or tooling, encouraging explicit package imports and correct packaging behavior.

### Configuration Files

- Root `pyproject.toml` contains workspace membership (`[tool.uv.workspace] members = [...]`), shared settings for ruff/mypy/pytest/coverage, and dev dependencies under `optional-dependencies.dev`.
- Component `pyproject.toml` (e.g. `src/gmail_client_impl/pyproject.toml`) declares the component-specific dependencies and build metadata. The component config extends root tooling (for formatting, etc.) and is the unit that gets packaged if you build that component.

### Package Structure

- Each package under `src/` has an `__init__.py` to make it an explicit package. Keep `__init__.py` thin — export the public API surface and avoid heavy imports or side effects. A small `__all__` and a couple of import shims is fine; avoid importing large optional dependencies at import time.

### Import Guidelines

- Prefer absolute imports using the package name (e.g. `from mail_client_api.message import Message`).
- Use relative imports only inside a package for nearby modules (e.g. `from . import helpers`) when it improves readability and avoids circular imports.
- Tests are executed with `--import-mode=importlib` and a configured `pythonpath` so absolute imports resolve to the `src` packages; avoid relying on implicit `sys.path` hacks.

## Testing Strategy

### Testing Philosophy

- Fast, deterministic unit tests first. Isolate external dependencies by mocking the network and credentials.
- Integration tests verify real interactions with third-party APIs and are run in CI only in protected branches when credentials are provided.
- Use pytest markers to classify tests (`unit`, `integration`, `e2e`, `circleci`, `local_credentials`).

### Test Organization

- Unit tests: `src/*/tests/` — focus on implementation units and function-level behavior.
- Component tests: component-level `tests/` directories that exercise that component.
- Integration and E2E tests: top-level `tests/integration/` and `tests/e2e/`.

### Test **init**.py convention

- Prefer not to add `__init__.py` files inside test directories unless you need old-style package test imports. Tests are executed as modules (importlib mode) and keeping tests as plain modules avoids import-time side effects and accidental package-level behavior. If you must create a package-level test module, keep `__init__.py` minimal.

### Test Abstraction Levels

- Unit tests: single function/class, mock external systems.
- Integration tests: test component interactions (may call Google APIs with credentials).
- E2E: full scenario tests that simulate the user flow across components.

### Code Coverage

- Tool: `pytest-cov` / coverage (configured through `pyproject.toml`).
- Minimum threshold: 85% (`fail_under = 85`) as configured in the root and component `pyproject.toml` files.

Run tests with coverage (local)

```bash
# create and activate venv (see Development Tools section for uv commands)
uv venv --python 3.11
source .venv/bin/activate
uv sync --all-packages --extra dev

# Run the full test suite with coverage
pytest src/ tests/ --cov=src --cov-report=term-missing

# Run only unit tests (fast)
pytest src/ -m unit --maxfail=1 -q

# Run all tests except ones that need local credentials
pytest src/ tests/ -m "not local_credentials"
```

## Development Tools

This project uses uv (https://astral.sh/uv) to manage a multi-component workspace. The root `pyproject.toml` lists workspace members.

**Key `uv` commands**

```bash
# Create and activate a virtual environment for the workspace
uv venv --python 3.11
source .venv/bin/activate

# Install all workspace packages + dev extras
uv sync --all-packages --extra dev

# Show workspace membership and available commands
uv tree

# Install an extra tool temporarily into the venv
uv add <package>
```

**Role of root vs component pyproject.toml**

- Root `pyproject.toml` configures workspace members, shared tool settings and developer/test extras.
- Component `pyproject.toml` files describe the component's packaging metadata and component-scoped dependencies.

### Static Analysis & Formatting

**Tools used**

- `Ruff` — linting and auto-formatting.
- `mypy` — static type checking.

Run checks locally

```bash
source .venv/bin/activate
# Lint and auto-fix
ruff check .

# Type check
mypy src/ --explicit-package-bases
```

Why this matters

- Consistent formatting and type checking prevents subtle bugs and keeps contributions reviewable and fast to merge. The tools are configured in `pyproject.toml`. Ruff settings are extended by component packages.

### Documentation Generation

**Tooling**

- MkDocs with Material theme and `mkdocstrings` is configured in root optional dependencies. Docs live in `docs/` and MkDocs configuration is in `mkdocs.yml`.

**Local preview**

```bash
source .venv/bin/activate
mkdocs serve
```

**Build site**

```bash
mkdocs build
```

### Continuous Integration (CircleCI)

Pipeline overview (see `.circleci/config.yml`)

- `build` — installs uv, creates the virtualenv, syncs dependencies, persists the workspace. Runs on all feature branches but ignores `main`, `develop`, and a few protected branches.
- `lint` — runs ruff linting using the persisted venv.
- `unit_test` — runs fast unit tests, coverage, and mypy. Tests must meet `--cov-fail-under=85`.
- `circleci_test` — runs most tests (except local-credentials tests) and collects results.
- `integration_test` — optional job that runs on protected branches (`main`, `develop`) and requires a CircleCI context containing `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `DISCORD_CLIENT_ID` , `DISCORD_CLIENT_SECRET` , `DISCORD_BOT_TOKEN` `DISCORD_REDIRECT_URI`
- `report_summary` — collects and prints summaries and artifacts.

Triggers & contexts

- The normal `build_and_test` workflow runs on feature branches (excluding protected branches). The `full_integration` workflow (which includes `integration_test`) runs only on `main`/`develop` and branches explicitly listed.

### How to Contribute (Practical Checklist)

1. Create a topic branch from `main` as appropriate.
2. Run formatting/linting and fix issues locally: `ruff check .` and `mypy src/`.
3. Run the unit test suite and ensure coverage: `pytest src/ --cov=src --cov-fail-under=85`.
4. Open a PR describing the change with tests attached. If your change requires integration-level verification, document how a reviewer can run integration tests (credentials, env var names) or add a CI context request.

For any questions, please refer to the README.md of this repository.
