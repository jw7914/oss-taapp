"""Edge case tests for the colocated GTaskList implementation."""

import json

import pytest

from gtask_client_impl.tasklist_impl import GTaskList


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    VERY_LONG_TITLE_MIN_LENGTH = 1000
    VERY_LONG_ETAG_MIN_LENGTH = 500

    def test_extremely_large_tasklist_id(self) -> None:
        """Test handling of extremely large tasklist IDs."""
        long_id = "x" * 1000
        tasklist_data = {
            "id": long_id,
            "title": "Long ID Test",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == long_id
        assert tasklist.title == "Long ID Test"

    def test_unicode_in_tasklist_content(self) -> None:
        """Test handling of Unicode characters in title."""
        tasklist_data = {
            "id": "unicode123",
            "title": "🎉 Unicode Test 测试 🌟",
            "etag": "etag_测试_🎉",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert "Unicode Test" in tasklist.title
        assert "🎉" in tasklist.title
        assert "etag_测试_🎉" in tasklist.etag

    def test_very_long_title(self) -> None:
        """Test handling of very long title."""
        long_title = "Very Long Title " * 100
        tasklist_data = {
            "id": "longtitle123",
            "title": long_title,
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.title == long_title
        assert len(tasklist.title) > self.VERY_LONG_TITLE_MIN_LENGTH

    def test_very_long_etag(self) -> None:
        """Test handling of very long ETag."""
        long_etag = 'W/"etag_value_' + "x" * 500 + '"'
        tasklist_data = {
            "id": "longetag123",
            "title": "Long ETag Test",
            "etag": long_etag,
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.title == "Long ETag Test"
        assert len(tasklist.etag) > self.VERY_LONG_ETAG_MIN_LENGTH
        assert "etag_value_" in tasklist.etag

    def test_malformed_json(self) -> None:
        """Test handling of malformed JSON data raises ValueError."""
        malformed_json = '{"id": "test", "title": "Test", invalid}'

        with pytest.raises(ValueError, match="Failed to parse tasklist data"):
            GTaskList(raw_data=malformed_json)

    def test_empty_json_string(self) -> None:
        """Test handling of empty JSON string."""
        empty_json = "{}"

        tasklist = GTaskList(raw_data=empty_json)

        assert tasklist.id == ""
        assert tasklist.title == ""
        assert tasklist.etag == ""
        assert tasklist.updated == ""
        assert tasklist.self_link == ""

    def test_invalid_json(self) -> None:
        """Test handling of completely invalid JSON."""
        invalid_json = "This is not JSON at all!!!"

        with pytest.raises(ValueError, match="Failed to parse tasklist data"):
            GTaskList(raw_data=invalid_json)

    def test_whitespace_only_json(self) -> None:
        """Test JSON string that is only whitespace characters raises ValueError."""
        whitespace_json = "   \t\n  "

        with pytest.raises(ValueError, match="Failed to parse tasklist data"):
            GTaskList(raw_data=whitespace_json)

    def test_non_ascii_tasklist_id(self) -> None:
        """Test non-ASCII characters in tasklist ID."""
        unicode_id = "tasklist_测试_🎉_123"
        tasklist_data = {
            "id": unicode_id,
            "title": "Unicode ID Test",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == unicode_id
        assert tasklist.title == "Unicode ID Test"

    def test_nested_json_structure(self) -> None:
        """Test JSON with nested structures (should ignore extra nested data)."""
        tasklist_data = {
            "id": "nested123",
            "title": "Nested Test",
            "extra": {
                "nested": {"data": "ignored"},
                "array": [1, 2, 3],
            },
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "nested123"
        assert tasklist.title == "Nested Test"

    def test_tasklist_with_null_values(self) -> None:
        """Test tasklist containing null values for optional fields."""
        tasklist_data = {
            "id": "null123",
            "title": "Null Test",
            "etag": None,
            "updated": None,
            "selfLink": None,
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "null123"
        assert tasklist.title == "Null Test"
        assert tasklist.etag is None
        assert tasklist.updated is None
        assert tasklist.self_link is None

    def test_repeated_property_access(self) -> None:
        """Test that accessing properties multiple times yields consistent results."""
        tasklist_data = {
            "id": "repeat123",
            "title": "Repeat Test",
            "etag": "etag_repeat",
            "updated": "2025-07-30T10:30:00Z",
            "selfLink": "https://www.googleapis.com/tasks/v1/lists/repeat123",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        for _ in range(5):
            assert tasklist.id == "repeat123"
            assert tasklist.title == "Repeat Test"
            assert tasklist.etag == "etag_repeat"
            assert tasklist.updated == "2025-07-30T10:30:00Z"
            assert tasklist.self_link == "https://www.googleapis.com/tasks/v1/lists/repeat123"

    def test_tasklist_with_only_id_and_title(self) -> None:
        """Test tasklist that contains only id and title fields."""
        tasklist_data = {
            "id": "minimal123",
            "title": "Minimal Fields",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "minimal123"
        assert tasklist.title == "Minimal Fields"
        assert tasklist.etag == ""
        assert tasklist.updated == ""
        assert tasklist.self_link == ""

    def test_tasklist_with_rfc3339_timestamp_variations(self) -> None:
        """Test tasklist with various RFC 3339 timestamp formats."""
        tasklist_data = {
            "id": "rfc3339_123",
            "title": "RFC 3339 Test",
            "updated": "2025-07-30T10:30:00Z",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.updated == "2025-07-30T10:30:00Z"

    def test_tasklist_with_extra_unexpected_fields(self) -> None:
        """Test JSON with extra fields not part of the tasklist schema."""
        tasklist_data = {
            "id": "extra123",
            "title": "Extra Fields Test",
            "unknown_field": "should be ignored",
            "another_unknown": 12345,
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "extra123"
        assert tasklist.title == "Extra Fields Test"

    def test_tasklist_with_numeric_id(self) -> None:
        """Test tasklist with numeric ID (should be converted to string)."""
        tasklist_data = {
            "id": "12345",
            "title": "Numeric ID Test",
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.id == "12345"
        assert tasklist.title == "Numeric ID Test"

    def test_tasklist_with_complex_self_link(self) -> None:
        """Test tasklist with complex selfLink URL."""
        complex_link = (
            "https://www.googleapis.com/tasks/v1/users/@me/lists/tasklist123?fields=id,title"
        )
        tasklist_data = {
            "id": "complexlink123",
            "title": "Complex Self Link Test",
            "selfLink": complex_link,
        }

        raw_data = json.dumps(tasklist_data)
        tasklist = GTaskList(raw_data=raw_data)

        assert tasklist.self_link == complex_link

    def test_tasklist_with_etag_variations(self) -> None:
        """Test tasklist with different ETag formats."""
        etag_variations = [
            'W/"etag_value"',
            "etag_simple",
            'W/"etag_with_special_chars_!@#$%"',
        ]

        for etag in etag_variations:
            tasklist_data = {
                "id": f"etag_{etag_variations.index(etag)}",
                "title": "ETag Variation Test",
                "etag": etag,
            }

            raw_data = json.dumps(tasklist_data)
            tasklist = GTaskList(raw_data=raw_data)

            assert tasklist.etag == etag
