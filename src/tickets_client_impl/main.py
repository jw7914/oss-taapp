"""Main module for demonstrating the tickets client."""

import logging

import gtask_client_impl  # noqa: F401
from tickets_api import TicketStatus

from tickets_client_impl import TicketsClient

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _initialize_client() -> TicketsClient | None:
    """Initialize the tickets client.

    Returns:
        TicketsClient instance if successful, None otherwise.

    """
    logger.info("\n[1] Initializing TicketsClient...")
    try:
        client = TicketsClient(interactive=False)
        logger.info("✓ TicketsClient initialized successfully")
    except Exception:
        logger.exception("✗ Failed to initialize TicketsClient")
        return None
    else:
        return client


def _test_create_ticket(client: TicketsClient) -> str | None:
    """Test creating a ticket.

    Args:
        client: The tickets client instance.

    Returns:
        The created ticket ID if successful, None otherwise.

    """
    logger.info("\n[2] Creating a new ticket...")
    try:
        ticket = client.create_ticket(
            title="Test Ticket - Bug Fix",
            description="This is a test ticket for demonstrating the tickets client",
        )
        logger.info("✓ Ticket created successfully")
        logger.info("  ID: %s", ticket.id)
        logger.info("  Title: %s", ticket.title)
        logger.info("  Description: %s", ticket.description)
        logger.info("  Status: %s", ticket.status)
    except Exception:
        logger.exception("✗ Failed to create ticket")
        return None
    else:
        return ticket.id


def _test_get_ticket(client: TicketsClient, ticket_id: str) -> None:
    """Test retrieving a ticket by ID.

    Args:
        client: The tickets client instance.
        ticket_id: The ID of the ticket to retrieve.

    """
    logger.info("\n[3] Retrieving ticket by ID...")
    try:
        retrieved_ticket = client.get_ticket(ticket_id)
        if retrieved_ticket:
            logger.info("✓ Ticket retrieved successfully")
            logger.info("  ID: %s", retrieved_ticket.id)
            logger.info("  Title: %s", retrieved_ticket.title)
            logger.info("  Status: %s", retrieved_ticket.status)
        else:
            logger.warning("✗ Ticket not found")
    except Exception:
        logger.exception("✗ Failed to retrieve ticket")


def _test_search_by_status(client: TicketsClient) -> None:
    """Test searching tickets by status.

    Args:
        client: The tickets client instance.

    """
    logger.info("\n[4] Searching tickets by status (OPEN)...")
    try:
        open_tickets = client.search_tickets(status=TicketStatus.OPEN)
        logger.info("✓ Found %d open ticket(s)", len(open_tickets))
        for i, ticket in enumerate(open_tickets[:3], 1):  # Show first 3
            logger.info("  %d. %s (ID: %s)", i, ticket.title, ticket.id)
    except Exception:
        logger.exception("✗ Failed to search tickets")


def _test_search_by_query(client: TicketsClient) -> None:
    """Test searching tickets by query.

    Args:
        client: The tickets client instance.

    """
    logger.info("\n[5] Searching tickets by query ('test')...")
    try:
        matching_tickets = client.search_tickets(query="test")
        logger.info("✓ Found %d ticket(s) matching 'test'", len(matching_tickets))
        for i, ticket in enumerate(matching_tickets[:3], 1):  # Show first 3
            logger.info("  %d. %s (ID: %s)", i, ticket.title, ticket.id)
    except Exception:
        logger.exception("✗ Failed to search tickets")


def _test_update_ticket_status(client: TicketsClient, ticket_id: str) -> str | None:
    """Test updating ticket status.

    Args:
        client: The tickets client instance.
        ticket_id: The ID of the ticket to update.

    Returns:
        The updated ticket ID if successful, None otherwise.

    """
    logger.info("\n[6] Updating ticket status to IN_PROGRESS...")
    try:
        updated_ticket = client.update_ticket(ticket_id=ticket_id, status=TicketStatus.IN_PROGRESS)
        logger.info("✓ Ticket updated successfully")
        logger.info("  ID: %s", updated_ticket.id)
        logger.info("  Title: %s", updated_ticket.title)
        logger.info("  Status: %s", updated_ticket.status)
    except Exception:
        logger.exception("✗ Failed to update ticket")
        return None
    else:
        return updated_ticket.id  # Update ID in case it changed


def _test_update_ticket_title(client: TicketsClient, ticket_id: str) -> str | None:
    """Test updating ticket title.

    Args:
        client: The tickets client instance.
        ticket_id: The ID of the ticket to update.

    Returns:
        The updated ticket ID if successful, None otherwise.

    """
    logger.info("\n[7] Updating ticket title...")
    try:
        updated_ticket = client.update_ticket(
            ticket_id=ticket_id, title="Test Ticket - Updated Title",
        )
        logger.info("✓ Ticket title updated successfully")
        logger.info("  New Title: %s", updated_ticket.title)
        logger.info("  Status: %s", updated_ticket.status)
    except Exception:
        logger.exception("✗ Failed to update ticket")
        return None
    else:
        return updated_ticket.id  # Update ID in case it changed


def _test_list_all_tickets(client: TicketsClient) -> None:
    """Test listing all tickets.

    Args:
        client: The tickets client instance.

    """
    logger.info("\n[8] Listing all tickets...")
    try:
        all_tickets = client.search_tickets()
        logger.info("✓ Found %d total ticket(s)", len(all_tickets))
        for i, ticket in enumerate(all_tickets[:5], 1):  # Show first 5
            status_emoji = (
                "✓"
                if ticket.status == TicketStatus.CLOSED
                else "○"
                if ticket.status == TicketStatus.OPEN
                else "→"
            )
            logger.info(
                "  %d. %s %s (ID: %s, Status: %s)",
                i,
                status_emoji,
                ticket.title,
                ticket.id,
                ticket.status,
            )
    except Exception:
        logger.exception("✗ Failed to list tickets")


def _test_delete_ticket_info() -> None:
    """Display information about delete ticket test (skipped)."""
    logger.info("\n[9] Delete ticket test (SKIPPED - to preserve test data)")
    logger.info("  To test deletion, uncomment the code below:")
    logger.info("  # success = client.delete_ticket(test_ticket_id)")
    logger.info("  # logger.info('✓ Ticket deleted: %s', success)")


def main() -> None:
    """Initialize the tickets client and demonstrate all ticket methods."""
    logger.info("=" * 60)
    logger.info("TICKETS CLIENT DEMONSTRATION")
    logger.info("=" * 60)

    # Initialize the tickets client
    client = _initialize_client()
    if client is None:
        return

    # Test 1: Create a ticket
    test_ticket_id = _test_create_ticket(client)
    if test_ticket_id is None:
        return

    # Test 2: Get a ticket
    _test_get_ticket(client, test_ticket_id)

    # Test 3: Search tickets by status
    _test_search_by_status(client)

    # Test 4: Search tickets by query
    _test_search_by_query(client)

    # Test 5: Update ticket status
    updated_id = _test_update_ticket_status(client, test_ticket_id)
    if updated_id is not None:
        test_ticket_id = updated_id

    # Test 6: Update ticket title
    updated_id = _test_update_ticket_title(client, test_ticket_id)
    if updated_id is not None:
        test_ticket_id = updated_id

    # Test 7: Search all tickets
    _test_list_all_tickets(client)

    # Test 8: Delete ticket (optional - commented out to preserve test data)
    _test_delete_ticket_info()

    logger.info("\n%s", "=" * 60)
    logger.info("DEMONSTRATION COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
