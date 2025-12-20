"""Public API for the openai_client_impl package."""

from .ai_client import AIClientImpl as AIClientImpl
from .errors import MissingOpenAIKeyError as MissingOpenAIKeyError
from .storage import (
    init_db as init_db,
)
from .storage import (
    set_openai_key as set_openai_key,
)

__version__ = "0.1.0"
