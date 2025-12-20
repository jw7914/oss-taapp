"""Tests for Ticket implementation."""

from task_client_api import task
from tickets_api import TicketStatus

from tickets_client_impl.ticket_impl import Ticket


class MockTask(task.Task):
    """Mock Task for testing."""

    def __init__(
        self,
        task_id: str,
        title: str,
        notes: str | None = None,
        status: str = "needsAction",
    ) -> None:
        """Initialize mock task."""
        self._id = task_id
        self._title = title
        self._notes = notes
        self._status = status

    @property
    def id(self) -> str:
        """Return task ID."""
        return self._id

    @property
    def title(self) -> str:
        """Return task title."""
        return self._title

    @property
    def notes(self) -> str | None:
        """Return task notes."""
        return self._notes

    @property
    def status(self) -> str:
        """Return task status."""
        return self._status

    @property
    def due(self) -> str | None:
        """Return due date."""
        return None

    @property
    def completed(self) -> str | None:
        """Return completion date."""
        return None

    @property
    def deleted(self) -> bool:
        """Return deleted status."""
        return False

    @property
    def hidden(self) -> bool:
        """Return hidden status."""
        return False


class TestTicketImpl:
    """Test cases for Ticket implementation."""

    def test_ticket_open_status(self) -> None:
        """Test ticket with OPEN status."""
        task_obj = MockTask("task1", "Test Task", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.id == "task1"
        assert ticket.title == "Test Task"
        assert ticket.description == "Description"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.assignee is None

    def test_ticket_in_progress_status(self) -> None:
        """Test ticket with IN_PROGRESS status (has (IP) prefix)."""
        task_obj = MockTask("task2", "(IP) In Progress Task", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.id == "task2"
        assert ticket.title == "In Progress Task"  # Prefix removed
        assert ticket.description == "Description"
        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.assignee is None

    def test_ticket_closed_status(self) -> None:
        """Test ticket with CLOSED status."""
        task_obj = MockTask("task3", "Completed Task", "Description", "completed")
        ticket = Ticket(task_obj)

        assert ticket.id == "task3"
        assert ticket.title == "Completed Task"
        assert ticket.description == "Description"
        assert ticket.status == TicketStatus.CLOSED
        assert ticket.assignee is None

    def test_ticket_closed_with_ip_prefix(self) -> None:
        """Test ticket that is closed but has (IP) prefix (should still be CLOSED)."""
        task_obj = MockTask("task4", "(IP) Closed Task", "Description", "completed")
        ticket = Ticket(task_obj)

        assert ticket.id == "task4"
        assert ticket.title == "Closed Task"  # Prefix removed
        assert ticket.status == TicketStatus.CLOSED  # Status takes precedence

    def test_ticket_no_description(self) -> None:
        """Test ticket with no description."""
        task_obj = MockTask("task5", "No Description Task", None, "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.id == "task5"
        assert ticket.title == "No Description Task"
        assert ticket.description == ""  # None becomes empty string
        assert ticket.status == TicketStatus.OPEN

    def test_ticket_empty_title(self) -> None:
        """Test ticket with empty title."""
        task_obj = MockTask("task6", "", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.id == "task6"
        assert ticket.title == ""
        assert ticket.description == "Description"
        assert ticket.status == TicketStatus.OPEN

    def test_ticket_ip_prefix_in_middle(self) -> None:
        """Test that (IP) prefix only matches at the start."""
        task_obj = MockTask("task7", "Task (IP) in middle", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.title == "Task (IP) in middle"  # Not removed
        assert ticket.status == TicketStatus.OPEN  # Not IN_PROGRESS

    def test_ticket_ip_prefix_case_sensitive(self) -> None:
        """Test that (IP) prefix is case sensitive."""
        task_obj = MockTask("task8", "(ip) lowercase prefix", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.title == "(ip) lowercase prefix"  # Not removed
        assert ticket.status == TicketStatus.OPEN  # Not IN_PROGRESS

    def test_ticket_assignee_always_none(self) -> None:
        """Test that assignee is always None."""
        task_obj = MockTask("task9", "Task", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.assignee is None
