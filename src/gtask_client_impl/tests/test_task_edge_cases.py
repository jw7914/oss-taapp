"""Edge case tests for the colocated GTask implementation."""

import json

import pytest

from gtask_client_impl.task_impl import GTask


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    VERY_LONG_TITLE_MIN_LENGTH = 1000
    VERY_LONG_NOTES_MIN_LENGTH = 30000

    def test_extremely_large_task_id(self) -> None:
        """Test handling of extremely large task IDs."""
        long_id = "x" * 1000
        task_data = {
            "id": long_id,
            "title": "Long ID Test",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == long_id
        assert task.title == "Long ID Test"

    def test_unicode_in_task_content(self) -> None:
        """Test handling of Unicode characters in title and notes."""
        task_data = {
            "id": "unicode123",
            "title": "🎉 Unicode Test 测试 🌟",
            "notes": "Unicode notes: こんにちは 世界! 🌍 Café naïve résumé",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert "Unicode Test" in task.title
        assert "🎉" in task.title
        assert task.notes is not None
        assert "こんにちは 世界! 🌍" in task.notes
        assert "Café naïve résumé" in task.notes

    def test_very_long_title(self) -> None:
        """Test handling of very long title."""
        long_title = "Very Long Title " * 100
        task_data = {
            "id": "longtitle123",
            "title": long_title,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.title == long_title
        assert len(task.title) > self.VERY_LONG_TITLE_MIN_LENGTH

    def test_very_long_notes(self) -> None:
        """Test handling of very long notes."""
        long_notes = "This is a very very long note. " * 1000
        task_data = {
            "id": "longnotes123",
            "title": "Long Notes Test",
            "notes": long_notes,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.title == "Long Notes Test"
        assert task.notes is not None
        assert len(task.notes) > self.VERY_LONG_NOTES_MIN_LENGTH
        assert "This is a very very long note." in task.notes

    def test_malformed_json(self) -> None:
        """Test handling of malformed JSON data."""
        malformed_json = '{"id": "test", "title": "Test", invalid}'

        task = GTask(raw_data=malformed_json)

        assert task.id == ""  # Empty dict defaults
        assert task.title == ""
        assert task.notes is None
        assert task.status == "needsAction"
        assert task.deleted is False
        assert task.hidden is False

    def test_empty_json_string(self) -> None:
        """Test handling of empty JSON string."""
        empty_json = ""

        with pytest.raises(ValueError, match="Failed to parse task data"):
            GTask(raw_data=empty_json)

    def test_invalid_json(self) -> None:
        """Test handling of completely invalid JSON."""
        invalid_json = "This is not JSON at all!!!"

        with pytest.raises(ValueError, match="Failed to parse task data"):
            GTask(raw_data=invalid_json)

    def test_whitespace_only_json(self) -> None:
        """Test JSON string that is only whitespace characters."""
        whitespace_json = "   \t\n  "

        with pytest.raises(ValueError, match="Failed to parse task data"):
            GTask(raw_data=whitespace_json)

    def test_non_ascii_task_id(self) -> None:
        """Test non-ASCII characters in task ID."""
        unicode_id = "task_测试_🎉_123"
        task_data = {
            "id": unicode_id,
            "title": "Unicode ID Test",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == unicode_id

    def test_nested_json_structure(self) -> None:
        """Test JSON with nested structures (should ignore extra nested data)."""
        task_data = {
            "id": "nested123",
            "title": "Nested Test",
            "extra": {
                "nested": {"data": "ignored"},
                "array": [1, 2, 3],
            },
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "nested123"
        assert task.title == "Nested Test"

    def test_task_with_null_values(self) -> None:
        """Test task containing null values for optional fields."""
        task_data = {
            "id": "null123",
            "title": "Null Test",
            "notes": None,
            "due": None,
            "completed": None,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "null123"
        assert task.title == "Null Test"
        assert task.notes is None
        assert task.due is None
        assert task.completed is None

    def test_task_with_only_id_and_title(self) -> None:
        """Test task that contains only id and title fields."""
        task_data = {
            "id": "minimal123",
            "title": "Minimal Fields",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "minimal123"
        assert task.title == "Minimal Fields"
        assert task.notes is None
        assert task.status == "needsAction"
        assert task.due is None
        assert task.completed is None
        assert task.deleted is False
        assert task.hidden is False

    def test_task_with_boolean_edge_cases(self) -> None:
        """Test task with boolean values set explicitly."""
        task_data_true = {
            "id": "booltrue123",
            "title": "Boolean True",
            "deleted": True,
            "hidden": True,
        }

        task_data_false = {
            "id": "boolfalse123",
            "title": "Boolean False",
            "deleted": False,
            "hidden": False,
        }

        raw_data_true = json.dumps(task_data_true)
        raw_data_false = json.dumps(task_data_false)

        task_true = GTask(raw_data=raw_data_true)
        task_false = GTask(raw_data=raw_data_false)

        assert task_true.deleted is True
        assert task_true.hidden is True
        assert task_false.deleted is False
        assert task_false.hidden is False

    def test_task_with_rfc3339_timestamp_variations(self) -> None:
        """Test task with various RFC 3339 timestamp formats."""
        task_data = {
            "id": "rfc3339_123",
            "title": "RFC 3339 Test",
            "due": "2025-07-30T10:30:00Z",
            "completed": "2025-07-29T15:45:00+00:00",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.due == "2025-07-30T10:30:00Z"
        assert task.completed == "2025-07-29T15:45:00+00:00"

    def test_task_with_extra_unexpected_fields(self) -> None:
        """Test JSON with extra fields not part of the task schema."""
        task_data = {
            "id": "extra123",
            "title": "Extra Fields Test",
            "unknown_field": "should be ignored",
            "another_unknown": 12345,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "extra123"
        assert task.title == "Extra Fields Test"

    def test_task_with_numeric_id(self) -> None:
        """Test task with numeric ID (should be converted to string)."""
        task_data = {
            "id": "12345",
            "title": "Numeric ID Test",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "12345"  # JSON number gets converted
        assert task.title == "Numeric ID Test"
