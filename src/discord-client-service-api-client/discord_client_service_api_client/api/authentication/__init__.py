"""Contains endpoint functions for accessing the API.

This module re-exports the generated endpoint modules under short, stable
names so callers can import endpoints like:

        from discord_client_service_api_client.api.authentication import login

and then call `login.sync_detailed(...)` just like the mail client adapter does.
"""

from . import auth_callback_auth_callback_get as auth_callback
from . import login_login_get as login

__all__ = ["login", "auth_callback"]
