"""Re-export commonly used message-related endpoints under short names.

This mirrors the convenient import style used by the mail adapter so callers
can do e.g.: from discord_client_service_api_client.api.messages import get_messages
and then call `get_messages.sync_detailed(...)`.
"""

from . import delete_message_channels_channel_id_messages_message_id_delete as delete_message
from . import get_message_channels_channel_id_messages_message_id_get as get_message
from . import list_channel_messages_channels_channel_id_messages_get as get_messages
from . import send_message_message_recipient_id_post as send_message

__all__ = ["get_messages", "get_message", "delete_message", "send_message"]
"""Contains endpoint functions for accessing the API"""
