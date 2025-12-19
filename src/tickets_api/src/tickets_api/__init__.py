"""Abstract interfaces for Ticketing APIs."""

from abc import ABC, abstractmethod
from enum import StrEnum


class TicketStatus(StrEnum):
    """Enumeration of possible ticket statuses."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Ticket(ABC):
    """Abstract representation of a Ticket."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the ticket."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """The title of the ticket."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """The detailed description of the ticket."""
        raise NotImplementedError

    @property
    @abstractmethod
    def status(self) -> TicketStatus:
        """The current status of the ticket."""
        raise NotImplementedError

    @property
    @abstractmethod
    def assignee(self) -> str | None:
        """The ID of the user assigned to the ticket, if any."""
        raise NotImplementedError


class TicketInterface(ABC):
    """The contract for Ticketing services."""

    @abstractmethod
    def create_ticket(self, title: str, description: str, assignee: str | None = None) -> Ticket:
        """Create a new ticket."""
        raise NotImplementedError

    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Ticket | None:
        """Retrieve a ticket by its ID."""
        raise NotImplementedError

    @abstractmethod
    def search_tickets(self, query: str | None = None, status: TicketStatus | None = None) -> list[Ticket]:
        """Search for tickets based on query and/or status."""
        raise NotImplementedError

    @abstractmethod
    def update_ticket(
        self,
        ticket_id: str,
        status: TicketStatus | None = None,
        title: str | None = None,
    ) -> Ticket:
        """Update a ticket's details."""
        raise NotImplementedError

    @abstractmethod
    def delete_ticket(self, ticket_id: str) -> bool:
        """Delete a ticket. Returns True if successful."""
        raise NotImplementedError
