from fastapi import FastAPI, Request, WebSocketDisconnect
import json

from fastapi import FastAPI
from starlette.websockets import WebSocket
from fastapi.middleware.cors import CORSMiddleware

from livestream import (
    get_user_token,
    setup_church_livestream_channel,
)
from models.channel_response_model import ChurchChannelResponse
from models.user_token_model import GetTokenResponse
from webhook_handler import handle_webhook_event
from comments_websocket.comments_socket import WebSocketHandler


app = FastAPI()


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
