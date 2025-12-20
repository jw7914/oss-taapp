"""Re-export user-related endpoints under short names for convenience."""

from . import get_current_user_user_get as get_current_user
from . import get_users_serverusers_guild_id_get as get_users

__all__ = ["get_current_user", "get_users"]
"""Contains endpoint functions for accessing the API"""
