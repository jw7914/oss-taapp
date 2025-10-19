"""FastAPI Gmail client service.

Endpoints:
- "/"         : Welcome message.
- "/login"    : Authenticate Gmail account.
- "/messages" : List messages.
- "/messages/{id}" : Message details.
- "/messages/{id}/mark-as-read" : Mark as read.
- "/messages/{id}" (DELETE): Delete message.

Requires FastAPI, mail_client_api, gmail_client_impl.
Run to start API and manage Gmail via HTTP.
"""

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
import gmail_client_impl  # noqa: F401
import mail_client_api

app = FastAPI(
    title="Mail Client Service API",
    description="A Restful FastAPI service for managing Gmail messages",
    version="1.0.0"
)


@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    """Return a welcome message for the Mail Client Service."""
    return {"message": "Welcome to Mail Client Service!"}

@app.get("/login", tags=["Authentication"], summary="Authenticate Gmail Account")
def login(interactive: bool = Query(False, description="Whether to use interactive authentication")) -> JSONResponse:
    """Authenticate the user's Gmail account.

    Args:
        interactive (bool): Whether to use interactive authentication.

    Returns:
        JSONResponse: Success message if authenticated, error details if failed.

    Raises:
        HTTPException: 500 if authentication fails, 409 if already authenticated.

    """
    # Check if already authenticated by checking if client exists in app state
    if hasattr(app.state, "client") and app.state.client is not None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Already authenticated", "status": "success"},
        )

    try:
        # Attempt authentication
        # Prevent multiple simultaneous authentication attempts
        if getattr(app.state, "auth_in_progress", False):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Authentication in progress",
                    "message": "Authentication is already in progress. Please wait.",
                    "status": "error",
                },
            )
        app.state.auth_in_progress = True
        try:
            client = mail_client_api.get_client(interactive=interactive) # type: ignore[attr-defined]
        finally:
            app.state.auth_in_progress = False

        # Store client in application state
        app.state.client = client

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Authentication successful", "status": "success"},
        )

    except RuntimeError as e:
        # Handle authentication errors (missing credentials, invalid tokens, etc.)
        error_message = str(e)
        if "No valid credentials found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Authentication failed",
                    "message": (
                        "No valid credentials found. Please ensure credentials.json exists or environment variables are set."
                    ),
                    "status": "error",
                },
            ) from e
        if "Interactive authentication failed" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Authentication failed",
                    "message": "Interactive authentication failed. Please try again.",
                    "status": "error",
                },
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Authentication error",
                "message": error_message,
                "status": "error",
            },
        ) from e

    except FileNotFoundError as e:
        # Handle missing credentials.json file
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Configuration error",
                "message": "credentials.json file not found. Please ensure it exists in the project root.",
                "status": "error",
            },
        ) from e

    except Exception as e:
        # Handle any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Unexpected error",
                "message": f"An unexpected error occurred during authentication: {e!s}",
                "status": "error",
            },
        ) from e

@app.get("/logout", tags=["Authentication"], summary="Logout Gmail Account")
def logout() -> JSONResponse:
    """Logout the authenticated Gmail account by clearing the client from app state."""
    if hasattr(app.state, "client") and app.state.client is not None:
        app.state.client = None
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Logged out successfully", "status": "success"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "No active session to logout", "status": "success"},
    )

@app.get("/messages", tags=["Messages"], summary="Get Messages", description="Retrieve a list of Gmail messages with optional limit")
def get_messages(max_results: int = Query(3, ge=1, le=100, description="Maximum number of messages to return")) -> JSONResponse:
    """Get messages from the authenticated Gmail client.
    Args:
        max_results (int): Maximum number of messages to return (default: 3, min: 1, max: 100).
    Returns:
        JSONResponse: List of messages if successful, error details if failed.
    Raises:
        HTTPException: 401 if not authenticated, 500 if message retrieval fails.
    """
    # Check if user is authenticated
    if not hasattr(app.state, "client") or app.state.client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Not authenticated",
                "message": "User is not authenticated. Please log in first.",
                "status": "error",
            },
        )

    # Validate max_results query parameter
    if not isinstance(max_results, int) or max_results < 1 or max_results > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Invalid query parameter",
                "message": "max_results must be an integer between 1 and 100.",
                "status": "error",
            },
        )

    try:
        messages = list(app.state.client.get_messages(max_results=max_results))

        # Convert GmailMessage objects to dictionaries for JSON serialization
        serialized_messages = []
        for message in messages:
            serialized_messages.append(
                {
                    "id": message.id,
                    "from": message.from_,
                    "to": message.to,
                    "date": message.date,
                    "subject": message.subject,
                    "body": message.body,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"messages": serialized_messages, "status": "success"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to fetch messages",
                "message": str(e),
                "status": "error",
            },
        ) from e


@app.get("/messages/{message_id}", tags=["Messages"], summary="Get Message Details", description="Retrieve detailed information for a specific message by ID")
def get_message_detail(message_id: str) -> JSONResponse:
    """Fetch the full detail of a single message by its ID.
    Args:
        message_id (str): The ID of the message to fetch.
    Returns:
        JSONResponse: The message details if successful, error details if failed.
    Raises:
        HTTPException: 401 if not authenticated, 404 if message not found, 500 for other errors.
    """
    # Check if user is authenticated
    if not hasattr(app.state, "client") or app.state.client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Not authenticated",
                "message": "User is not authenticated. Please log in first.",
                "status": "error",
            },
        )
    try:
        message = app.state.client.get_message(message_id)
        if message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Message not found",
                    "message": f"No message found with ID: {message_id}",
                    "status": "error",
                },
            )
        message_dict = {
            "id": message.id,
            "from": message.from_,
            "to": message.to,
            "date": message.date,
            "subject": message.subject,
            "body": message.body,
        }
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": message_dict, "status": "success"},
        )
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)

        # Handle Gmail API 404 errors specifically
        if "404" in error_str and "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Message not found",
                    "message": f"Message with ID '{message_id}' does not exist in your Gmail account.",
                    "status": "error",
                },
            ) from e

        # Handle other Gmail API errors
        if "HttpError" in error_str:
            # Extract status code from HttpError if possible
            if "400" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Bad request",
                        "message": f"Invalid message ID format: {message_id}",
                        "status": "error",
                    },
                ) from e
            elif "403" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Access forbidden",
                        "message": "Access to this message is forbidden. Check your Gmail permissions.",
                        "status": "error",
                    },
                ) from e

        # Generic fallback for other errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to fetch message",
                "message": f"An unexpected error occurred while fetching the message: {error_str}",
                "status": "error",
            },
        ) from e


@app.post("/messages/{message_id}/mark-as-read", tags=["Messages"], summary="Mark Message as Read", description="Mark a specific message as read by its ID")
def mark_message_as_read(message_id: str) -> JSONResponse:
    """Mark a message as read by its ID.
    Args:
        message_id (str): The ID of the message to mark as read.
    Returns:
        JSONResponse: Success message if marked as read, error details if failed.
    Raises:
        HTTPException: 401 if not authenticated, 404 if message not found, 500 for other errors.
    """
    # Check if user is authenticated
    if not hasattr(app.state, "client") or app.state.client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Not authenticated",
                "message": "User is not authenticated. Please log in first.",
                "status": "error",
            },
        )
    try:
        result = app.state.client.mark_as_read(message_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Message not found",
                    "message": f"No message found with ID: {message_id}",
                    "status": "error",
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Message {message_id} marked as read.", "status": "success"},
        )
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "404" in error_str and "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Message not found",
                    "message": f"Message with ID '{message_id}' does not exist in your Gmail account.",
                    "status": "error",
                },
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to mark as read",
                "message": f"An unexpected error occurred: {error_str}",
                "status": "error",
            },
        ) from e


@app.delete("/messages/{message_id}", tags=["Messages"], summary="Delete Message", description="Permanently delete a message by its ID")
def delete_message(message_id: str) -> JSONResponse:
    """Delete a message by its ID.
    Args:
        message_id (str): The ID of the message to delete.
    Returns:
        JSONResponse: Success message if deleted, error details if failed.
    Raises:
        HTTPException: 401 if not authenticated, 404 if message not found, 500 for other errors.
    """
    # Check if user is authenticated
    if not hasattr(app.state, "client") or app.state.client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Not authenticated",
                "message": "User is not authenticated. Please log in first.",
                "status": "error",
            },
        )
    try:
        result = app.state.client.delete_message(message_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Message not found",
                    "message": f"No message found with ID: {message_id}",
                    "status": "error",
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Message {message_id} deleted successfully.", "status": "success"},
        )
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "404" in error_str and "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Message not found",
                    "message": f"Message with ID '{message_id}' does not exist in your Gmail account.",
                    "status": "error",
                },
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to delete message",
                "message": f"An unexpected error occurred: {error_str}",
                "status": "error",
            },
        ) from e
