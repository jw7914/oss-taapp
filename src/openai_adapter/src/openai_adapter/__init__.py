"""AI Service Adapter.

This package provides an adapter that exposes a small, stable API for
consumers and forwards calls to the OpenAI Client Service using explicit HTTP
calls.
"""

from ._adapter import (
    AdapterAPIError as AdapterAPIError,
)
from ._adapter import (
    OpenAIServiceAdapter as OpenAIServiceAdapter,
)
