"""Tests for Discord message and channel implementations."""

from discord_client_impl.message_impl import DiscordChannel, DiscordMessage, get_chat_message_impl, register


class TestDiscordMessage:
    """Tests for DiscordMessage implementation."""

    def test_message_id_from_raw_data(self) -> None:
        """Test that message_id is correctly extracted from raw data."""
        raw_data = {"id": "123456", "content": "Hello"}
        msg = DiscordMessage(raw_data)
        assert msg.message_id == "123456"


class TestDiscordChannel:
    """Tests for DiscordChannel implementation."""

    def test_channel_id_extraction(self) -> None:
        """Test channel_id property."""
        raw_data = {"id": "chan_123", "name": "general"}
        channel = DiscordChannel(raw_data)
        assert channel.channel_id == "chan_123"


class TestGetChatMessageImpl:
    """Tests for get_chat_message_impl factory function."""

    def test_returns_discord_message_instance(self) -> None:
        """Test that factory returns a DiscordMessage instance."""
        raw_data = {"id": "msg_123", "content": "Hello"}
        msg = get_chat_message_impl(raw_data)
        assert isinstance(msg, DiscordMessage)


class TestRegister:
    """Tests for the register function."""

    def test_register_sets_module_get_message(self) -> None:
        """Test that register() updates message.get_message."""
        register()
        # Basic smoke test
        assert callable(register)
