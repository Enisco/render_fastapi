from fastapi import FastAPI, Request, WebSocketDisconnect, UploadFile, File, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json

from starlette.websockets import WebSocket
from fastapi.middleware.cors import CORSMiddleware

from devotionals_service.devotional_service import process_devotional_document
from livestream import (
    get_user_token,
    setup_church_livestream_channel,
)
from models.channel_response_model import ChurchChannelResponse
from models.user_token_model import GetTokenResponse
from webhook_handler import handle_webhook_event
from comments_websocket.comments_socket import WebSocketHandler


app = FastAPI()

# Initialize HTTPBearer for receiving tokens
security = HTTPBearer()


# To allow CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gospeltube-livestream-test-server.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello, from GTube Livestream server, with comments WebSocket"}


@app.post("/receive_webhook")
async def receive_webhook_event(request: Request):
    """
    This is the endpoint that receives the Webhook event from Stream.io.
    """
    try:
        print("Receiving Event Notification from Stream's Webhook")
        body = await request.json()
        print(body)
        handle_webhook_event(body)

    except Exception as error:
        print("Error occured: ", error)

    return {"message": "Webhook received successfully"}


@app.get(
    "/user/get_token/{user_id}",
    # response_model=GetTokenResponse,
)
async def generate_token(user_id: str):
    """
    Generate a livestream token for a user.
    """
    return get_user_token(user_id)


@app.get(
    "/church/create_livestream_channel/{church_id}",
    # response_model=ChurchChannelResponse,
)
async def create_church_livestream_channel(church_id: str):
    """
    Create a livestream channel for a new church.
    'church_id' is the church's streamID generated during church account creation in the onboarding.
    """
    return setup_church_livestream_channel(church_id)


# Chat Websocket endpoint

manager = WebSocketHandler()


@app.websocket("/ws/{topic}")
async def comments_websocket_endpoint(websocket: WebSocket, topic: str):
    """FastAPI WebSocket route that interacts with WebSocketHandler."""

    print("Topic received from client: ", topic)

    await manager.connect(websocket, topic)
    try:
        while True:
            data = await websocket.receive_text()  # Receive message from client
            print(f"Message received on topic {topic}: {data}")

            # Acknowledge receipt
            ack_message = json.dumps({"ack": f"Received '{data}' on topic '{topic}'"})
            await websocket.send_text(ack_message)

            # Broadcast message to all clients in the topic
            await manager.send_message(topic, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket, topic)


# Bulk devotional upload endpoint

@app.post("/devotional/upload_doc/{church_id}")
async def upload_file(
    church_id: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    """Handle file upload, extract text, and return structured devotionals."""

    token = credentials.credentials
    print(f"Received file for church {church_id}")
    print(f"Token received: {token}")

    # Dummy function to process document (Replace with actual logic)
    def process_devotional_document(filename):
        return json.dumps({"message": f"Processed file: {filename}", "token": token})

    response = process_devotional_document(file.filename)

    try:
        admonitions_data = json.loads(response)
        return admonitions_data
    except json.JSONDecodeError as e:
        return {"error": f"Error parsing response: {str(e)}"}


# python -m venv venv
# venv\Scripts\activate
# pip freeze > requirements.txt

# deepseek_ai_api_key = 'sk-630b91e4926e42b7b1eb097ffe5a4c02'
# gemini_ai_api_key = 'AIzaSyDgFx4bfhJG4RkzxEs10J6yZkK-3jVfYmU'
