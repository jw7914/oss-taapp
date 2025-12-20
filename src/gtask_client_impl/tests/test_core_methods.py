"""Unit tests for GTaskClient core methods.

This module contains comprehensive unit tests for the core business logic
of the GTaskClient class, mocking all external dependencies.
"""

import json
from unittest.mock import Mock, patch

import pytest
from googleapiclient.errors import HttpError

from gtask_client_impl.gtask_impl import GTaskClient

# Constants for Tasks API values
DEFAULT_TASKLIST_ID = "@default"
TEST_TASKLIST_ID = "test_tasklist_123"
TEST_TASK_ID = "test_task_123"


class TestGTaskClientTaskOperations:
    """Test cases for GTaskClient task operations with mocked dependencies."""

    def setup_method(self) -> None:
        """Create a GTaskClient with mocked service."""
        self.mock_service = Mock()
        self.client = GTaskClient(service=self.mock_service)

    def test_get_task_success(self) -> None:
        """Test successful task retrieval."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID
        task_id = TEST_TASK_ID
        task_data = {"id": task_id, "title": "Test Task", "status": "needsAction"}
        raw_content = json.dumps(task_data)

        # Mock the Tasks API call chain
        mock_tasks = Mock()
        mock_get = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.get.return_value = mock_get
        mock_get.execute.return_value = task_data

        # Mock the task factory
        mock_task = Mock()
        with patch(
            "gtask_client_impl.gtask_impl.task.get_task",
            return_value=mock_task,
        ) as mock_factory:
            # ACT
            result = self.client.get_task(tasklist_id, task_id)

            # ASSERT
            assert result is mock_task
            mock_tasks.get.assert_called_once_with(
                tasklist=tasklist_id,
                task=task_id,
            )
            mock_get.execute.assert_called_once()
            mock_factory.assert_called_once_with(raw_data=raw_content)

    def test_get_task_api_exception(self) -> None:
        """Test get_task when Tasks API raises an exception."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID
        task_id = TEST_TASK_ID

        mock_tasks = Mock()
        mock_get = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.get.return_value = mock_get
        mock_get.execute.side_effect = HttpError(
            Mock(status=404, reason="Not Found"), b"Task not found",
        )

        # ACT & ASSERT
        with pytest.raises(ValueError, match=f"Failed to retrieve task {task_id}"):
            self.client.get_task(tasklist_id, task_id)

    def test_delete_task_success(self) -> None:
        """Test successful task deletion."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID
        task_id = TEST_TASK_ID

        mock_tasks = Mock()
        mock_delete = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.delete.return_value = mock_delete
        mock_delete.execute.return_value = None

        # ACT
        result = self.client.delete_task(tasklist_id, task_id)

        # ASSERT
        assert result is True
        mock_tasks.delete.assert_called_once_with(tasklist=tasklist_id, task=task_id)
        mock_delete.execute.assert_called_once()

    def test_delete_task_api_exception(self) -> None:
        """Test delete_task when Tasks API raises an exception."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID
        task_id = TEST_TASK_ID

        mock_tasks = Mock()
        mock_delete = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.delete.return_value = mock_delete
        error_response = Mock(status=500, reason="Internal Server Error")
        mock_delete.execute.side_effect = HttpError(error_response, b"Delete failed")

        # ACT
        result = self.client.delete_task(tasklist_id, task_id)

        # ASSERT
        assert result is False

    def test_list_tasks_success(self) -> None:
        """Test successful task listing."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID
        mock_tasks_list = [
            {"id": "task1", "title": "Task 1", "status": "needsAction"},
            {"id": "task2", "title": "Task 2", "status": "completed"},
            {"id": "task3", "title": "Task 3", "status": "needsAction"},
        ]

        # Mock the list call
        mock_tasks = Mock()
        mock_list = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.list.return_value = mock_list
        mock_list.execute.return_value = {"items": mock_tasks_list}

        # Mock the task factory
        mock_task_1 = Mock()
        mock_task_2 = Mock()
        mock_task_3 = Mock()

        with patch(
            "gtask_client_impl.gtask_impl.task.get_task",
            side_effect=[
                mock_task_1,
                mock_task_2,
                mock_task_3,
            ],
        ) as mock_factory:
            # ACT
            tasks = self.client.list_tasks(tasklist_id)

            # ASSERT
            assert len(tasks) == len(mock_tasks_list)
            assert tasks == [mock_task_1, mock_task_2, mock_task_3]

            # Verify list call
            mock_tasks.list.assert_called_once_with(tasklist=tasklist_id)

            # Verify factory calls
            assert mock_factory.call_count == len(mock_tasks_list)
            mock_factory.assert_any_call(raw_data=json.dumps(mock_tasks_list[0]))
            mock_factory.assert_any_call(raw_data=json.dumps(mock_tasks_list[1]))
            mock_factory.assert_any_call(raw_data=json.dumps(mock_tasks_list[2]))

    def test_list_tasks_empty_tasklist(self) -> None:
        """Test list_tasks when tasklist is empty."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID

        mock_tasks = Mock()
        mock_list = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        # ACT
        tasks = self.client.list_tasks(tasklist_id)

        # ASSERT
        assert len(tasks) == 0
        mock_tasks.list.assert_called_once_with(tasklist=tasklist_id)

    def test_list_tasks_no_items_key(self) -> None:
        """Test list_tasks when API response has no 'items' key."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID

        mock_tasks = Mock()
        mock_list = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.list.return_value = mock_list
        mock_list.execute.return_value = {}  # No 'items' key

        # ACT
        tasks = self.client.list_tasks(tasklist_id)

        # ASSERT
        assert len(tasks) == 0

    def test_list_tasks_api_exception(self) -> None:
        """Test list_tasks when Tasks API raises an exception."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID

        mock_tasks = Mock()
        mock_list = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.list.return_value = mock_list
        error_response = Mock(status=500, reason="Internal Server Error")
        mock_list.execute.side_effect = HttpError(error_response, b"List failed")

        # ACT
        tasks = self.client.list_tasks(tasklist_id)

        # ASSERT
        assert len(tasks) == 0

    def test_insert_task_success(self) -> None:
        """Test successful task insertion."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID
        task_data = {"id": TEST_TASK_ID, "title": "New Task", "status": "needsAction"}
        raw_content = json.dumps(task_data)

        # Mock task object
        mock_task_input = Mock()
        mock_task_input.title = "New Task"
        mock_task_input.notes = None
        mock_task_input.status = None
        mock_task_input.due = None

        # Mock the Tasks API call chain
        mock_tasks = Mock()
        mock_insert = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.insert.return_value = mock_insert
        mock_insert.execute.return_value = task_data

        # Mock the task factory
        mock_task_output = Mock()
        with patch(
            "gtask_client_impl.gtask_impl.task.get_task",
            return_value=mock_task_output,
        ) as mock_factory:
            # ACT
            result = self.client.insert_task(tasklist_id, mock_task_input)

            # ASSERT
            assert result is mock_task_output
            mock_tasks.insert.assert_called_once_with(
                tasklist=tasklist_id,
                body={"title": "New Task"},
            )
            mock_insert.execute.assert_called_once()
            mock_factory.assert_called_once_with(raw_data=raw_content)

    def test_insert_task_with_all_fields(self) -> None:
        """Test insert_task with all optional fields."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID
        task_data = {
            "id": TEST_TASK_ID,
            "title": "New Task",
            "notes": "Task notes",
            "status": "needsAction",
            "due": "2024-12-31T00:00:00Z",
        }

        # Mock task object with all fields
        mock_task_input = Mock()
        mock_task_input.title = "New Task"
        mock_task_input.notes = "Task notes"
        mock_task_input.status = "needsAction"
        mock_task_input.due = "2024-12-31T00:00:00Z"

        mock_tasks = Mock()
        mock_insert = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.insert.return_value = mock_insert
        mock_insert.execute.return_value = task_data

        mock_task_output = Mock()
        with patch(
            "gtask_client_impl.gtask_impl.task.get_task",
            return_value=mock_task_output,
        ):
            # ACT
            self.client.insert_task(tasklist_id, mock_task_input)

            # ASSERT
            mock_tasks.insert.assert_called_once_with(
                tasklist=tasklist_id,
                body={
                    "title": "New Task",
                    "notes": "Task notes",
                    "status": "needsAction",
                    "due": "2024-12-31T00:00:00Z",
                },
            )

    def test_insert_task_api_exception(self) -> None:
        """Test insert_task when Tasks API raises an exception."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID

        mock_task_input = Mock()
        mock_task_input.title = "New Task"
        mock_task_input.notes = None
        mock_task_input.status = None
        mock_task_input.due = None

        mock_tasks = Mock()
        mock_insert = Mock()

        self.mock_service.tasks.return_value = mock_tasks
        mock_tasks.insert.return_value = mock_insert
        error_response = Mock(status=400, reason="Bad Request")
        mock_insert.execute.side_effect = HttpError(error_response, b"Insert failed")

        # ACT & ASSERT
        with pytest.raises(HttpError):
            self.client.insert_task(tasklist_id, mock_task_input)


class TestGTaskClientTaskListOperations:
    """Test cases for GTaskClient tasklist operations with mocked dependencies."""

    def setup_method(self) -> None:
        """Create a GTaskClient with mocked service."""
        self.mock_service = Mock()
        self.client = GTaskClient(service=self.mock_service)

    def test_list_tasklists_success(self) -> None:
        """Test successful tasklist listing."""
        # ARRANGE
        mock_tasklists_list = [
            {"id": "list1", "title": "TaskList 1", "etag": "etag1"},
            {"id": "list2", "title": "TaskList 2", "etag": "etag2"},
            {"id": "list3", "title": "TaskList 3", "etag": "etag3"},
        ]

        # Mock the list call
        mock_tasklists = Mock()
        mock_list = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.list.return_value = mock_list
        mock_list.execute.return_value = {"items": mock_tasklists_list}

        # Mock the tasklist factory
        mock_tasklist_1 = Mock()
        mock_tasklist_2 = Mock()
        mock_tasklist_3 = Mock()

        with patch(
            "gtask_client_impl.gtask_impl.tasklist.get_tasklist",
            side_effect=[
                mock_tasklist_1,
                mock_tasklist_2,
                mock_tasklist_3,
            ],
        ) as mock_factory:
            # ACT
            tasklists = self.client.list_tasklists()

            # ASSERT
            assert len(tasklists) == len(mock_tasklists_list)
            assert tasklists == [mock_tasklist_1, mock_tasklist_2, mock_tasklist_3]

            # Verify list call
            mock_tasklists.list.assert_called_once()

            # Verify factory calls
            assert mock_factory.call_count == len(mock_tasklists_list)
            mock_factory.assert_any_call(raw_data=json.dumps(mock_tasklists_list[0]))
            mock_factory.assert_any_call(raw_data=json.dumps(mock_tasklists_list[1]))
            mock_factory.assert_any_call(raw_data=json.dumps(mock_tasklists_list[2]))

    def test_list_tasklists_empty(self) -> None:
        """Test list_tasklists when user has no tasklists."""
        # ARRANGE
        mock_tasklists = Mock()
        mock_list = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        # ACT
        tasklists = self.client.list_tasklists()

        # ASSERT
        assert len(tasklists) == 0
        mock_tasklists.list.assert_called_once()

    def test_list_tasklists_no_items_key(self) -> None:
        """Test list_tasklists when API response has no 'items' key."""
        # ARRANGE
        mock_tasklists = Mock()
        mock_list = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.list.return_value = mock_list
        mock_list.execute.return_value = {}  # No 'items' key

        # ACT
        tasklists = self.client.list_tasklists()

        # ASSERT
        assert len(tasklists) == 0

    def test_list_tasklists_api_exception(self) -> None:
        """Test list_tasklists when Tasks API raises an exception."""
        # ARRANGE
        mock_tasklists = Mock()
        mock_list = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.list.return_value = mock_list
        error_response = Mock(status=500, reason="Internal Server Error")
        mock_list.execute.side_effect = HttpError(error_response, b"List failed")

        # ACT
        tasklists = self.client.list_tasklists()

        # ASSERT
        assert len(tasklists) == 0

    def test_insert_tasklist_success(self) -> None:
        """Test successful tasklist insertion."""
        # ARRANGE
        tasklist_data = {
            "id": TEST_TASKLIST_ID,
            "title": "New TaskList",
            "etag": "etag123",
        }
        raw_content = json.dumps(tasklist_data)

        # Mock tasklist object
        mock_tasklist_input = Mock()
        mock_tasklist_input.title = "New TaskList"

        # Mock the TaskLists API call chain
        mock_tasklists = Mock()
        mock_insert = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.insert.return_value = mock_insert
        mock_insert.execute.return_value = tasklist_data

        # Mock the tasklist factory
        mock_tasklist_output = Mock()
        with patch(
            "gtask_client_impl.gtask_impl.tasklist.get_tasklist",
            return_value=mock_tasklist_output,
        ) as mock_factory:
            # ACT
            result = self.client.insert_tasklist(mock_tasklist_input)

            # ASSERT
            assert result is mock_tasklist_output
            mock_tasklists.insert.assert_called_once_with(body={"title": "New TaskList"})
            mock_insert.execute.assert_called_once()
            mock_factory.assert_called_once_with(raw_data=raw_content)

    def test_insert_tasklist_api_exception(self) -> None:
        """Test insert_tasklist when Tasks API raises an exception."""
        # ARRANGE
        mock_tasklist_input = Mock()
        mock_tasklist_input.title = "New TaskList"

        mock_tasklists = Mock()
        mock_insert = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.insert.return_value = mock_insert
        error_response = Mock(status=400, reason="Bad Request")
        mock_insert.execute.side_effect = HttpError(error_response, b"Insert failed")

        # ACT & ASSERT
        with pytest.raises(HttpError):
            self.client.insert_tasklist(mock_tasklist_input)

    def test_delete_tasklist_success(self) -> None:
        """Test successful tasklist deletion."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID

        mock_tasklists = Mock()
        mock_delete = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.delete.return_value = mock_delete
        mock_delete.execute.return_value = None

        # ACT
        result = self.client.delete_tasklist(tasklist_id)

        # ASSERT
        assert result is True
        mock_tasklists.delete.assert_called_once_with(tasklist=tasklist_id)
        mock_delete.execute.assert_called_once()

    def test_delete_tasklist_api_exception(self) -> None:
        """Test delete_tasklist when Tasks API raises an exception."""
        # ARRANGE
        tasklist_id = TEST_TASKLIST_ID

        mock_tasklists = Mock()
        mock_delete = Mock()

        self.mock_service.tasklists.return_value = mock_tasklists
        mock_tasklists.delete.return_value = mock_delete
        error_response = Mock(status=500, reason="Internal Server Error")
        mock_delete.execute.side_effect = HttpError(error_response, b"Delete failed")

        # ACT
        result = self.client.delete_tasklist(tasklist_id)

        # ASSERT
        assert result is False
