"""Tests for TicketsClient implementation."""

from unittest.mock import Mock

import pytest
from gtask_client_impl import GTaskClient
from task_client_api import task, tasklist
from tickets_api import TicketStatus

from tickets_client_impl.ticket_impl import Ticket
from tickets_client_impl.tickets_impl import TicketsClient


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


class MockTaskList(tasklist.TaskList):
    """Mock TaskList for testing."""

    def __init__(self, tasklist_id: str, title: str = "Default") -> None:
        """Initialize mock tasklist."""
        self._id = tasklist_id
        self._title = title

    @property
    def id(self) -> str:
        """Return tasklist ID."""
        return self._id

    @property
    def title(self) -> str:
        """Return tasklist title."""
        return self._title

    @property
    def etag(self) -> str:
        """Return etag."""
        return "etag"

    @property
    def updated(self) -> str:
        """Return updated timestamp."""
        return "2025-01-01T00:00:00Z"

    @property
    def self_link(self) -> str:
        """Return self link."""
        return "https://example.com/tasklist"


class TestTicketsClient:
    """Test cases for TicketsClient implementation."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_gtask_client = Mock(spec=GTaskClient)
        self.client = TicketsClient(gtask_client=self.mock_gtask_client)

        # Set up default tasklist
        default_tasklist = MockTaskList("@default", "Default TaskList")
        self.mock_gtask_client.list_tasklists.return_value = [default_tasklist]

    def test_create_ticket_open(self) -> None:
        """Test creating a ticket with OPEN status."""
        created_task = MockTask("task1", "New Task", "Description", "needsAction")
        self.mock_gtask_client.insert_task.return_value = created_task

        ticket = self.client.create_ticket("New Task", "Description")

        assert isinstance(ticket, Ticket)
        assert ticket.title == "New Task"
        assert ticket.description == "Description"
        assert ticket.status == TicketStatus.OPEN

        # Verify insert_task was called with correct parameters
        self.mock_gtask_client.insert_task.assert_called_once()
        call_args = self.mock_gtask_client.insert_task.call_args
        assert call_args[0][0] == "@default"  # tasklist_id
        task_obj = call_args[0][1]
        assert task_obj.title == "New Task"
        assert task_obj.notes == "Description"
        assert task_obj.status == "needsAction"

    def test_create_ticket_empty_description(self) -> None:
        """Test creating a ticket with empty description."""
        created_task = MockTask("task2", "Task", None, "needsAction")
        self.mock_gtask_client.insert_task.return_value = created_task

        ticket = self.client.create_ticket("Task", "")

        assert ticket.title == "Task"
        assert ticket.description == ""

    def test_get_ticket_success(self) -> None:
        """Test getting a ticket successfully."""
        task_obj = MockTask("task1", "Test Task", "Description", "needsAction")
        self.mock_gtask_client.get_task.return_value = task_obj

        ticket = self.client.get_ticket("task1")

        assert ticket is not None
        assert isinstance(ticket, Ticket)
        assert ticket.id == "task1"
        assert ticket.title == "Test Task"
        self.mock_gtask_client.get_task.assert_called_once_with("@default", "task1")

    def test_get_ticket_not_found(self) -> None:
        """Test getting a ticket that doesn't exist."""
        self.mock_gtask_client.get_task.side_effect = ValueError("Task not found")

        ticket = self.client.get_ticket("nonexistent")

        assert ticket is None

    def test_search_tickets_by_query(self) -> None:
        """Test searching tickets by query."""
        tasks = [
            MockTask("task1", "Bug fix", "Fix the bug", "needsAction"),
            MockTask("task2", "Feature", "Add new feature", "needsAction"),
            MockTask("task3", "Bug report", "Report bug", "needsAction"),
        ]
        self.mock_gtask_client.list_tasks.return_value = tasks

        results = self.client.search_tickets(query="bug")

        expected_bug_tickets = 2
        assert len(results) == expected_bug_tickets
        assert all(
            "bug" in result.title.lower() or "bug" in result.description.lower()
            for result in results
        )

    def test_search_tickets_by_status(self) -> None:
        """Test searching tickets by status."""
        tasks = [
            MockTask("task1", "Task 1", "Description", "needsAction"),
            MockTask("task2", "(IP) Task 2", "Description", "needsAction"),
            MockTask("task3", "Task 3", "Description", "completed"),
        ]
        self.mock_gtask_client.list_tasks.return_value = tasks

        open_tickets = self.client.search_tickets(status=TicketStatus.OPEN)
        assert len(open_tickets) == 1
        assert open_tickets[0].status == TicketStatus.OPEN

        in_progress_tickets = self.client.search_tickets(status=TicketStatus.IN_PROGRESS)
        assert len(in_progress_tickets) == 1
        assert in_progress_tickets[0].status == TicketStatus.IN_PROGRESS

        closed_tickets = self.client.search_tickets(status=TicketStatus.CLOSED)
        assert len(closed_tickets) == 1
        assert closed_tickets[0].status == TicketStatus.CLOSED

    def test_search_tickets_by_query_and_status(self) -> None:
        """Test searching tickets by both query and status."""
        tasks = [
            MockTask("task1", "Bug fix", "Fix the bug", "needsAction"),
            MockTask("task2", "(IP) Bug fix in progress", "Fixing", "needsAction"),
            MockTask("task3", "Feature", "Add feature", "needsAction"),
            MockTask("task4", "Bug closed", "Fixed", "completed"),
        ]
        self.mock_gtask_client.list_tasks.return_value = tasks

        results = self.client.search_tickets(query="bug", status=TicketStatus.OPEN)
        assert len(results) == 1
        assert results[0].title == "Bug fix"

    def test_search_tickets_no_filters(self) -> None:
        """Test searching tickets with no filters."""
        tasks = [
            MockTask("task1", "Task 1", "Description", "needsAction"),
            MockTask("task2", "Task 2", "Description", "needsAction"),
        ]
        self.mock_gtask_client.list_tasks.return_value = tasks

        results = self.client.search_tickets()

        expected_ticket_count = 2
        assert len(results) == expected_ticket_count

    def test_update_ticket_status(self) -> None:
        """Test updating ticket status."""
        existing_task = MockTask("task1", "Task", "Description", "needsAction")
        updated_task = MockTask("task1_new", "(IP) Task", "Description", "needsAction")

        self.mock_gtask_client.get_task.return_value = existing_task
        self.mock_gtask_client.delete_task.return_value = True
        self.mock_gtask_client.insert_task.return_value = updated_task

        ticket = self.client.update_ticket("task1", status=TicketStatus.IN_PROGRESS)

        assert ticket.status == TicketStatus.IN_PROGRESS
        self.mock_gtask_client.delete_task.assert_called_once_with("@default", "task1")
        self.mock_gtask_client.insert_task.assert_called_once()

    def test_update_ticket_title(self) -> None:
        """Test updating ticket title."""
        existing_task = MockTask("task1", "Old Title", "Description", "needsAction")
        updated_task = MockTask("task1_new", "New Title", "Description", "needsAction")

        self.mock_gtask_client.get_task.return_value = existing_task
        self.mock_gtask_client.delete_task.return_value = True
        self.mock_gtask_client.insert_task.return_value = updated_task

        ticket = self.client.update_ticket("task1", title="New Title")

        assert ticket.title == "New Title"
        self.mock_gtask_client.delete_task.assert_called_once_with("@default", "task1")
        self.mock_gtask_client.insert_task.assert_called_once()

    def test_update_ticket_not_found(self) -> None:
        """Test updating a ticket that doesn't exist."""
        self.mock_gtask_client.get_task.side_effect = ValueError("Task not found")

        with pytest.raises(ValueError, match="Ticket task1 not found"):
            self.client.update_ticket("task1", title="New Title")

    def test_delete_ticket_success(self) -> None:
        """Test deleting a ticket successfully."""
        self.mock_gtask_client.delete_task.return_value = True

        result = self.client.delete_ticket("task1")

        assert result is True
        self.mock_gtask_client.delete_task.assert_called_once_with("@default", "task1")

    def test_delete_ticket_failure(self) -> None:
        """Test deleting a ticket that fails."""
        self.mock_gtask_client.delete_task.return_value = False

        result = self.client.delete_ticket("task1")

        assert result is False

    def test_default_tasklist_caching(self) -> None:
        """Test that default tasklist is cached."""
        default_tasklist = MockTaskList("@default", "Default")
        self.mock_gtask_client.list_tasklists.return_value = [default_tasklist]

        # First call should fetch tasklist
        self.client._get_default_tasklist_id()
        assert self.mock_gtask_client.list_tasklists.call_count == 1

        # Second call should use cache
        self.client._get_default_tasklist_id()
        assert self.mock_gtask_client.list_tasklists.call_count == 1

    def test_default_tasklist_not_available(self) -> None:
        """Test error when no tasklists are available."""
        self.mock_gtask_client.list_tasklists.return_value = []

        with pytest.raises(RuntimeError, match="No tasklists available"):
            self.client._get_default_tasklist_id()
