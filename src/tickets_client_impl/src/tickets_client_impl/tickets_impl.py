"""Tickets Interface Implementation using Google Tasks."""

import logging
from typing import TYPE_CHECKING

import gtask_client_impl
from gtask_client_impl.gtask_impl import GTaskClient as _GTaskClientImpl
from task_client_api import task
from tickets_api import Ticket as TicketABC
from tickets_api import TicketInterface, TicketStatus

from tickets_client_impl.ticket_impl import Ticket

if TYPE_CHECKING:
    from gtask_client_impl.gtask_impl import GTaskClient as _GTaskClient
else:
    _GTaskClient = _GTaskClientImpl

# Register gtask_client_impl to ensure it's available
gtask_client_impl.register()


class _TaskBuilder(task.Task):
    """Helper class to build Task objects for insertion."""

    def __init__(
        self,
        title: str,
        notes: str | None = None,
        status: str = "needsAction",
        due: str | None = None,
    ) -> None:
        """Initialize a Task builder.

        Args:
            title: Task title
            notes: Task notes
            status: Task status (needsAction or completed)
            due: Due date (RFC 3339 timestamp)

        """
        self._id = ""
        self._title = title
        self._notes = notes
        self._status = status
        self._due = due
        self._completed = None
        self._deleted = False
        self._hidden = False

    @property
    def id(self) -> str:
        """Return the unique identifier of the task."""
        return self._id

    @property
    def title(self) -> str:
        """Return the title of the task."""
        return self._title

    @property
    def notes(self) -> str | None:
        """Return the notes describing the task."""
        return self._notes

    @property
    def status(self) -> str:
        """Return the status of the task."""
        return self._status

    @property
    def due(self) -> str | None:
        """Return the due date of the task."""
        return self._due

    @property
    def completed(self) -> str | None:
        """Return the completion date of the task."""
        return self._completed

    @property
    def deleted(self) -> bool:
        """Return whether the task has been deleted."""
        return self._deleted

    @property
    def hidden(self) -> bool:
        """Return whether the task is hidden."""
        return self._hidden


class TicketsClient(TicketInterface):
    """Implementation of TicketInterface using Google Tasks."""

    IP_PREFIX = "(IP) "

    def __init__(
        self, gtask_client: _GTaskClient | None = None, *, interactive: bool = False,
    ) -> None:
        """Initialize the TicketsClient.

        Args:
            gtask_client: Optional GTaskClient instance. If None, creates a new one.
            interactive: If True, allows interactive authentication flow.

        """
        self.logger = logging.getLogger(__name__)
        if gtask_client is None:
            self._gtask_client = _GTaskClientImpl(interactive=interactive)
        else:
            self._gtask_client = gtask_client
        self._default_tasklist_id: str | None = None

    def _get_default_tasklist_id(self) -> str:
        """Get the default tasklist ID, caching it after first fetch.

        Returns:
            The ID of the default tasklist (first tasklist).

        Raises:
            RuntimeError: If no tasklists are available.

        """
        if self._default_tasklist_id is None:
            tasklists = self._gtask_client.list_tasklists()
            if not tasklists:
                error_msg = "No tasklists available"
                raise RuntimeError(error_msg)
            self._default_tasklist_id = tasklists[0].id
            self.logger.info("Cached default tasklist ID: %s", self._default_tasklist_id)
        return self._default_tasklist_id

    def _ticket_status_to_task_status(self, ticket_status: TicketStatus) -> str:
        """Convert TicketStatus to Google Tasks status.

        Args:
            ticket_status: The ticket status to convert.

        Returns:
            The corresponding Google Tasks status string.

        """
        if ticket_status == TicketStatus.CLOSED:
            return "completed"
        return "needsAction"

    def _apply_title_prefix(self, title: str, status: TicketStatus) -> str:
        """Apply or remove title prefix based on status.

        Args:
            title: The original title.
            status: The ticket status.

        Returns:
            The title with appropriate prefix applied.

        """
        # Remove existing prefix if present
        title = title.removeprefix(self.IP_PREFIX)

        # Add prefix for IN_PROGRESS
        if status == TicketStatus.IN_PROGRESS:
            return f"{self.IP_PREFIX}{title}"

        return title

    def _task_to_ticket(self, task_obj: task.Task) -> Ticket:
        """Convert a Task to a Ticket.

        Args:
            task_obj: The Task object to convert.

        Returns:
            A Ticket object.

        """
        return Ticket(task_obj)

    def create_ticket(self, title: str, description: str, assignee: str | None = None) -> TicketABC:
        """Create a new ticket.

        Args:
            title: The title of the ticket.
            description: The description of the ticket.
            assignee: The assignee (ignored, Google Tasks doesn't support assignees).

        Returns:
            The created Ticket.

        """
        # Google tasks doesn't support assignees, so we ignore the argument
        del assignee

        tasklist_id = self._get_default_tasklist_id()

        # Create task with OPEN status by default
        task_title = self._apply_title_prefix(title, TicketStatus.OPEN)
        task_status = self._ticket_status_to_task_status(TicketStatus.OPEN)

        task_obj = _TaskBuilder(
            title=task_title,
            notes=description or None,
            status=task_status,
        )

        created_task = self._gtask_client.insert_task(tasklist_id, task_obj)
        return self._task_to_ticket(created_task)

    def get_ticket(self, ticket_id: str) -> TicketABC | None:
        """Retrieve a ticket by its ID.

        Args:
            ticket_id: The ID of the ticket to retrieve.

        Returns:
            The Ticket if found, None otherwise.

        """
        tasklist_id = self._get_default_tasklist_id()

        try:
            task_obj = self._gtask_client.get_task(tasklist_id, ticket_id)
            return self._task_to_ticket(task_obj)
        except ValueError:
            # Task not found
            return None

    def search_tickets(
        self, query: str | None = None, status: TicketStatus | None = None,
    ) -> list[TicketABC]:
        """Search for tickets based on query and/or status.

        Args:
            query: Optional search query to match against title and notes.
            status: Optional status filter.

        Returns:
            A list of matching Tickets.

        """
        tasklist_id = self._get_default_tasklist_id()
        tasks = self._gtask_client.list_tasks(tasklist_id)

        matching_tickets: list[TicketABC] = []

        for task_obj in tasks:
            ticket = self._task_to_ticket(task_obj)

            # Filter by status if provided
            if status is not None and ticket.status != status:
                continue

            # Filter by query if provided
            if query is not None:
                query_lower = query.lower()
                title_match = query_lower in ticket.title.lower()
                description_match = query_lower in ticket.description.lower()
                if not (title_match or description_match):
                    continue

            matching_tickets.append(ticket)

        return matching_tickets

    def update_ticket(
        self,
        ticket_id: str,
        status: TicketStatus | None = None,
        title: str | None = None,
    ) -> TicketABC:
        """Update a ticket's details.

        Args:
            ticket_id: The ID of the ticket to update.
            status: Optional new status.
            title: Optional new title.

        Returns:
            The updated Ticket.

        Raises:
            ValueError: If the ticket is not found.

        """
        tasklist_id = self._get_default_tasklist_id()

        # Get existing ticket
        existing_ticket = self.get_ticket(ticket_id)
        if existing_ticket is None:
            error_msg = f"Ticket {ticket_id} not found"
            raise ValueError(error_msg)

        # Determine new values
        new_title = title if title is not None else existing_ticket.title
        new_status = status if status is not None else existing_ticket.status
        new_description = existing_ticket.description

        # Apply title prefix based on status
        task_title = self._apply_title_prefix(new_title, new_status)
        task_status = self._ticket_status_to_task_status(new_status)

        # Delete old task
        self._gtask_client.delete_task(tasklist_id, ticket_id)

        # Create new task with updated values
        task_obj = _TaskBuilder(
            title=task_title,
            notes=new_description or None,
            status=task_status,
        )

        created_task = self._gtask_client.insert_task(tasklist_id, task_obj)
        return self._task_to_ticket(created_task)

    def delete_ticket(self, ticket_id: str) -> bool:
        """Delete a ticket.

        Args:
            ticket_id: The ID of the ticket to delete.

        Returns:
            True if successful, False otherwise.

        """
        tasklist_id = self._get_default_tasklist_id()
        return self._gtask_client.delete_task(tasklist_id, ticket_id)
