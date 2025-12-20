"""Ticket Implementation that wraps Google Tasks."""

from task_client_api import task
from tickets_api import Ticket as TicketABC
from tickets_api import TicketStatus


class Ticket(TicketABC):
    """Concrete implementation of Ticket using Google Tasks."""

    IP_PREFIX = "(IP) "

    def __init__(self, task: task.Task) -> None:
        """Initialize a Ticket from a Task.

        Args:
            task: The underlying Task object from Google Tasks.

        """
        self._task = task

    @property
    def id(self) -> str:
        """Unique identifier for the ticket."""
        return self._task.id

    @property
    def title(self) -> str:
        """The title of the ticket."""
        title = self._task.title
        # Remove (IP) prefix if present
        if title.startswith(self.IP_PREFIX):
            return title[len(self.IP_PREFIX) :]
        return title

    @property
    def description(self) -> str:
        """The detailed description of the ticket."""
        return self._task.notes or ""

    @property
    def status(self) -> TicketStatus:
        """The current status of the ticket."""
        # If task is completed, ticket is CLOSED
        if self._task.status == "completed":
            return TicketStatus.CLOSED

        # If title starts with (IP) prefix, ticket is IN_PROGRESS
        if self._task.title.startswith(self.IP_PREFIX):
            return TicketStatus.IN_PROGRESS

        # Otherwise, ticket is OPEN
        return TicketStatus.OPEN

    @property
    def assignee(self) -> str | None:
        """The ID of the user assigned to the ticket, if any."""
        # Google Tasks doesn't support assignees
        return None
