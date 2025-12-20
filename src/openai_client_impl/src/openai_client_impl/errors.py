"""Custom exceptions for OpenAI client implementation."""


class MissingOpenAIKeyError(RuntimeError):
    """Raised when a user hasn't set an OpenAI API key yet."""
