from fastapi import FastAPI
import gmail_client_impl
import gmail_message_impl
import mail_client_api
from fastapi.responses import RedirectResponse

client = None
app = FastAPI()


@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/login")
def login():
    global client
    if client:
        return RedirectResponse(url="/messages")
    client = mail_client_api.get_client(interactive=True)
    print("\nSuccessfully authenticated and connected to the Gmail API.")

@app.get("/messages")
def get_messages():
    # return {"a":"a"}
    # Test 1: Get messages (existing functionality)
    global client
    if not client:
        return {"Message": "Please login"}
    print("\n=== TEST 1: Fetching Messages ===")
    client_messages = list(client.get_messages(max_results=3))
    
    return client_messages

@app.get("/messages/{message_id}")
def get_message(message_id):
    
    specific_msg = client.get_message(message_id)
    print("Successfully retrieved message:")
    print(f"  Subject: {specific_msg.subject}")
    print(f"  From: {specific_msg.from_}")
    print(f"  Date: {specific_msg.date}")
    return {"Subject": specific_msg.subject, "From": specific_msg.from_, "Date": specific_msg.date }
    

# @app.put("/messages/{message_id}")199631185300a694
# async def root(message_id):
#     return

# GET /messages: Fetches a list of message summaries.
# GET /messages/{message_id}: Fetches the full detail of a single message.
# DELETE /messages/{message_id}: Deletes a message.
# ... other ideas?
