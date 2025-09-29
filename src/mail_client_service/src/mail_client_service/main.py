import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

import gmail_client_impl  # noqa: F401
import gmail_message_impl  # noqa: F401
import mail_client_api

app = FastAPI()

@app.get("/")
def root() -> dict[str, str]:
    """Return a welcome message for the Mail Client Service."""
    return {"message": "Welcome to Mail Client Service!"}

@app.get("/login")
def login() -> JSONResponse:
    """Checks and returns the authentication status of the user's Gmail account."""
    if hasattr(app.state, "client") and app.state.client is not None:
        return JSONResponse(
            content={"message": "Client already authenticated."},
            status_code=status.HTTP_200_OK
        )
    try:
        app.state.client = mail_client_api.get_client(interactive=True)
        return JSONResponse(
            content={"message": "Client authenticated and stored."},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Authentication failed: {e!s}"},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
@app.get("/messages")
def get_messages() -> JSONResponse:
    """Retrieve the latest Gmail messages for the authenticated client."""
    if not hasattr(app.state, "client") or app.state.client is None:
        return JSONResponse(
            content={"error": "Client not authenticated. Please log in first."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    try:
        messages = list(app.state.client.get_messages(max_results=3))
        
        # Convert GmailMessage objects to dictionaries for JSON serialization
        serializable_messages = [
            {
                "id": msg.id,
                "from": msg.from_,
                "to": msg.to,
                "date": msg.date,
                "subject": msg.subject,
                "body": msg.body
            }
            for msg in messages
        ]
        
        return JSONResponse(
            content={"messages": serializable_messages},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to retrieve messages: {e!s}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@app.get("/messages/{message_id}")
def get_message_by_id(message_id: str) -> JSONResponse:
    """Retrieve a specific Gmail message by its ID."""
    if not hasattr(app.state, "client") or app.state.client is None:
        return JSONResponse(
            content={"error": "Client not authenticated. Please log in first."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Get the specific message by ID
        message = app.state.client.get_message(message_id)
        
        # Convert GmailMessage object to dictionary for JSON serialization
        serializable_message = {
            "id": message.id,
            "from": message.from_,
            "to": message.to,
            "date": message.date,
            "subject": message.subject,
            "body": message.body
        }
        
        return JSONResponse(
            content={"message": serializable_message},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to retrieve message {message_id}: {e!s}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.delete("/messages/{message_id}")
def delete_message_by_id(message_id: str) -> JSONResponse:
    """Delete a specific Gmail message by its ID."""
    if not hasattr(app.state, "client") or app.state.client is None:
        return JSONResponse(
            content={"error": "Client not authenticated. Please log in first."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Delete the specific message by ID
        success = app.state.client.delete_message(message_id)
        
        if success:
            return JSONResponse(
                content={"message": f"Message {message_id} deleted successfully."},
                status_code=status.HTTP_200_OK
            )
        
        return JSONResponse(
            content={"error": f"Failed to delete message {message_id}. Message may not exist or cannot be deleted."},
            status_code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to delete message {message_id}: {e!s}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
