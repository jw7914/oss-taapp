"""Tests for status mapping logic."""

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


class TestStatusMapping:
    """Test cases for status mapping edge cases."""

    def test_open_status_plain_title(self) -> None:
        """Test OPEN status with plain title."""
        task_obj = MockTask("task1", "Plain Task", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.OPEN
        assert ticket.title == "Plain Task"

    def test_open_status_with_spaces(self) -> None:
        """Test OPEN status with title that has spaces."""
        task_obj = MockTask("task2", "  Task with spaces  ", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.OPEN
        assert ticket.title == "  Task with spaces  "

    def test_in_progress_exact_prefix(self) -> None:
        """Test IN_PROGRESS with exact (IP) prefix."""
        task_obj = MockTask("task3", "(IP) Task", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.title == "Task"

    def test_in_progress_prefix_with_spaces(self) -> None:
        """Test IN_PROGRESS with (IP) prefix and spaces."""
        task_obj = MockTask("task4", "(IP)  Task with spaces", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.title == " Task with spaces"

    def test_closed_status_overrides_prefix(self) -> None:
        """Test that CLOSED status takes precedence over (IP) prefix."""
        task_obj = MockTask("task5", "(IP) Closed Task", "Description", "completed")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.CLOSED
        assert ticket.title == "Closed Task"

    def test_closed_status_plain_title(self) -> None:
        """Test CLOSED status with plain title."""
        task_obj = MockTask("task6", "Completed Task", "Description", "completed")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.CLOSED
        assert ticket.title == "Completed Task"

    def test_prefix_variations_not_matched(self) -> None:
        """Test that variations of (IP) prefix are not matched."""
        variations = [
            "(ip) lowercase",
            "(Ip) mixed case",
            "( IP) space before IP",
            "(IP ) space after IP",
            " (IP) space before",
            "(IP)",
            "IP) missing opening paren",
            "(IP missing closing paren",
        ]

        for title in variations:
            task_obj = MockTask("task", title, "Description", "needsAction")
            ticket = Ticket(task_obj)

            assert ticket.status == TicketStatus.OPEN, f"Title '{title}' should be OPEN"
            assert ticket.title == title, f"Title '{title}' should not be modified"

    def test_empty_title_open(self) -> None:
        """Test empty title with OPEN status."""
        task_obj = MockTask("task7", "", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.OPEN
        assert ticket.title == ""

    def test_empty_title_closed(self) -> None:
        """Test empty title with CLOSED status."""
        task_obj = MockTask("task8", "", "Description", "completed")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.CLOSED
        assert ticket.title == ""

    def test_unicode_in_title_with_prefix(self) -> None:
        """Test Unicode characters in title with (IP) prefix."""
        task_obj = MockTask("task9", "(IP) 🎉 Unicode Task 测试", "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.title == "🎉 Unicode Task 测试"

    def test_very_long_title_with_prefix(self) -> None:
        """Test very long title with (IP) prefix."""
        long_title_length = 1000
        long_title = "(IP) " + "A" * long_title_length
        task_obj = MockTask("task10", long_title, "Description", "needsAction")
        ticket = Ticket(task_obj)

        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.title == "A" * long_title_length
        assert len(ticket.title) == long_title_length
