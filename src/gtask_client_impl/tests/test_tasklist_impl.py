"""Tests for GTaskList implementation colocated with GTaskClient."""

import json

from gtask_client_impl.tasklist_impl import GTaskList


class TestGTaskList:
    """Test cases for the GTaskList class."""

    def test_basic_tasklist_creation(self) -> None:
        """Test creating a GTaskList with valid data."""
        tasklist_data = {
            "id": "tasklist123",
            "title": "Test TaskList",
            "etag": "etag123456",
            "updated": "2025-07-30T10:30:00Z",
            "selfLink": "https://www.googleapis.com/tasks/v1/lists/tasklist123",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "tasklist123"
        assert tasklist.title == "Test TaskList"
        assert tasklist.etag == "etag123456"
        assert tasklist.updated == "2025-07-30T10:30:00Z"
        assert tasklist.self_link == "https://www.googleapis.com/tasks/v1/lists/tasklist123"

    def test_tasklist_with_minimal_data(self) -> None:
        """Test tasklist with only required fields (title)."""
        tasklist_data = {
            "id": "minimal123",
            "title": "Minimal TaskList",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "minimal123"
        assert tasklist.title == "Minimal TaskList"
        assert tasklist.etag == ""  # Default value
        assert tasklist.updated == ""  # Default value
        assert tasklist.self_link == ""  # Default value

    def test_tasklist_with_all_fields(self) -> None:
        """Test tasklist with all fields populated."""
        tasklist_data = {
            "id": "full123",
            "title": "Complete TaskList",
            "etag": "etag789012",
            "updated": "2025-07-30T15:45:00Z",
            "selfLink": "https://www.googleapis.com/tasks/v1/lists/full123",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "full123"
        assert tasklist.title == "Complete TaskList"
        assert tasklist.etag == "etag789012"
        assert tasklist.updated == "2025-07-30T15:45:00Z"
        assert tasklist.self_link == "https://www.googleapis.com/tasks/v1/lists/full123"

    def test_tasklist_with_etag(self) -> None:
        """Test tasklist with ETag field."""
        tasklist_data = {
            "id": "etag123",
            "title": "TaskList with ETag",
            "etag": 'W/"etag_value_123"',
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.etag == 'W/"etag_value_123"'

    def test_tasklist_with_updated_timestamp(self) -> None:
        """Test tasklist with updated timestamp (RFC 3339)."""
        tasklist_data = {
            "id": "updated123",
            "title": "TaskList with Updated",
            "updated": "2025-08-15T23:59:59Z",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.updated == "2025-08-15T23:59:59Z"

    def test_tasklist_with_self_link(self) -> None:
        """Test tasklist with selfLink field."""
        tasklist_data = {
            "id": "selflink123",
            "title": "TaskList with Self Link",
            "selfLink": "https://www.googleapis.com/tasks/v1/lists/selflink123",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.self_link == "https://www.googleapis.com/tasks/v1/lists/selflink123"

    def test_tasklist_with_empty_strings(self) -> None:
        """Test tasklist with empty string values."""
        tasklist_data = {
            "id": "",
            "title": "",
            "etag": "",
            "updated": "",
            "selfLink": "",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == ""
        assert tasklist.title == ""
        assert tasklist.etag == ""
        assert tasklist.updated == ""
        assert tasklist.self_link == ""
