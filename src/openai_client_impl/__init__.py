"""Public exports and compatibility shims for the OpenAI client implementation."""

from __future__ import annotations

import sys
from importlib import import_module

_ai_client = import_module("openai_client_impl.src.openai_client_impl.ai_client")
_storage = import_module("openai_client_impl.src.openai_client_impl.storage")
_response = import_module("openai_client_impl.src.openai_client_impl.response")
_errors = import_module("openai_client_impl.src.openai_client_impl.errors")

sys.modules.setdefault("openai_client_impl.ai_client", _ai_client)
sys.modules.setdefault("openai_client_impl.storage", _storage)
sys.modules.setdefault("openai_client_impl.response", _response)
sys.modules.setdefault("openai_client_impl.errors", _errors)

ai_client = _ai_client
storage = _storage
response = _response
errors = _errors

AIClientImpl = _ai_client.AIClientImpl
MissingOpenAIKeyError = _ai_client.MissingOpenAIKeyError
init_db = _storage.init_db
set_openai_key = _storage.set_openai_key
