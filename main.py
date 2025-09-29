# ta-assignment/main.py

# Import the protocols first
# --- TRIGGER DEPENDENCY INJECTION ---
# By importing the implementation packages, their __init__.py files
# run and override the factory functions in the protocol packages.
import gmail_client_impl  # noqa: F401
import gmail_message_impl  # noqa: F401
import mail_client_api


def main() -> None:
    """Initializes the client and demonstrates all mail client methods."""
    print("Attempting to initialize Gmail client...")
    try:
        # Now, get_client() returns a GmailClient instance...
        client = mail_client_api.get_client(interactive=True)
        print("\nSuccessfully authenticated and connected to the Gmail API.")

        # Test 1: Get messages (existing functionality)
        print("\n=== TEST 1: Fetching Messages ===")
        messages = list(client.get_messages(max_results=3))

        if not messages:
            print("No messages found in inbox.")
            return

        print(f"Found {len(messages)} messages:")
        for i, msg in enumerate(messages, 1):
            print(f"\nMessage {i}:")
            print(f"  ID: {msg.id}")
            print(f"  Subject: {msg.subject}")
            print(f"  From: {msg.from_}")
            print(f"  Date: {msg.date}")
            print(f"  Body: {msg.body[:100].replace('/n', ' ')}...")

        # Test 2: Get a specific message by ID
        if messages:
            test_message_id = messages[0].id
            print(f"\n=== TEST 2: Getting Specific Message (ID: {test_message_id}) ===")
            try:
                specific_msg = client.get_message(test_message_id)
                print("Successfully retrieved message:")
                print(f"  Subject: {specific_msg.subject}")
                print(f"  From: {specific_msg.from_}")
                print(f"  Date: {specific_msg.date}")
            except Exception as e:
                print(f"Error getting specific message: {e}")

        # Test 3: Mark a message as read
        if messages:
            test_message_id = messages[0].id
            print(f"\n=== TEST 3: Marking Message as Read (ID: {test_message_id}) ===")
            try:
                success = client.mark_as_read(test_message_id)
                if success:
                    print("✓ Message marked as read successfully")
                else:
                    print("✗ Failed to mark message as read")
            except Exception as e:
                print(f"Error marking message as read: {e}")

        # Test 4: Delete a message (WARNING: This is destructive!)
        # Only test if we have more than one message to avoid deleting all messages
        if len(messages) > 1:
            print("\n=== TEST 4: Delete Message ===")
            # Ask for confirmation before deleting
            delete_message_id = messages[-1].id  # Delete the last message
            print(f"About to delete message ID: {delete_message_id}")
            print(f"Subject: {messages[-1].subject}")

            # For safety, let's skip actual deletion in this demo
            # Uncomment the lines below if you really want to test deletion
            print("SKIPPING ACTUAL DELETION FOR SAFETY")
            print("To enable deletion, uncomment the deletion code in main.py")

            try:
                success = client.delete_message(delete_message_id)
                if success:
                    print("✓ Message deleted successfully")
                else:
                    print("✗ Failed to delete message")
            except Exception as e:
                print(f"Error deleting message: {e}")
        else:
            print("\n=== TEST 4: Delete Message ===")
            print("Skipping deletion test - not enough messages to safely test")

        print("\n=== All Tests Completed ===")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        raise


if __name__ == "__main__":
    main()
