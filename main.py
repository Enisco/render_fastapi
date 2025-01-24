from fastapi import FastAPI, HTTPException, Request
import json

from livestream import (
    get_user_token,
    setup_church_livestream_channel,
)
from models.channel_response_model import ChurchChannelResponse
from models.user_token_model import GetTokenResponse
from webhook_handler import handle_webhook_event


app = FastAPI()


@app.get("/")
def root():
    return {"message": "Hello, from GTube Livestream server"}


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
