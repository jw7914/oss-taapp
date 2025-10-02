from collections.abc import Iterator
import json

from mail_client_service_api_client import Client

from mail_client_service_api_client.api.authentication import *
from mail_client_service_api_client.api.messages import *
from mail_client_api.message import Message

import mail_client_api


class ServiceClientAdapter(mail_client_api.Client):
    """
    Adapter class for interacting with the mail client API using a fast API client

    Provides methods to get, delete, and mark messages as read, as well as to retrieve messages from inbox
    """
    def __init__(self):
        self.Client = Client(base_url = "http://127.0.0.1:8000")
        
    def login(self) -> Message:
        """Authenticates the user """
        
        return login.sync_detailed(
            client = self.Client,
        )
    
    def get_message(self, message_id: str) -> Message:
        """Return a message by its ID."""
        
        return get_message_by_id.sync_detailed(
            message_id = message_id,
            client = self.Client,
        )

    def delete_message(self, message_id: str) -> bool:
        """Delete a message by its ID."""
        return delete_message.sync_detailed(
            message_id = message_id,
            client = self.Client,
        )

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read by its ID."""
        return mark_message_as_read.sync_detailed(
            message_id = message_id,
            client = self.Client
        )

    def get_messages(self, max_results: int = 10) -> Iterator[Message]:
        """Return an iterator of messages from the inbox."""
        messages = get_messages.sync_detailed(
            client = self.Client,
        )
        content = json.loads(messages.content)
        max_results = min(max_results,len(content['messages']))
        return content['messages'][:max_results]
