import uvicorn
from fastapi import FastAPI
import mail_client_api

app = FastAPI()

@app.get("/")
def root() -> dict[str, str]:
    """Return a welcome message for the Mail Client Service."""
    return {"message": "Welcome to Mail Client Service!"}

@app.get("/login")
def login() -> dict[str, str]:
    """Checks and returns the authentication status of the user's Gmail account."""
    app.state.client = mail_client_api.get_client(interactive=True)
    return {"message": "Client authenticated and stored."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
