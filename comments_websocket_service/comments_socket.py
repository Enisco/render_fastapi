from fastapi import WebSocket
import asyncio
import json

import requests

"""
{
    "bearer_token": "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJzb2RlZXFlMDNAZ21haWwuY29tIiwicGVybWlzc2lvbnMiOiIiLCJyb2xlcyI6IlVTRVIiLCJpc3MiOiJzZWxmIiwiZXhwIjoxNzQ0NjkxNTQ0LCJpYXQiOjE3NDIwOTk1NDR9.MpDZyOIdEOOfAfBPXjwtWBSo9Fqk8ZLJ8nHEIM5nxSuSPh3CkOGSnaVyx-5oXFO9AVsGWR96Q-8RSNSA7O_edF-k7cFI05dt6zibpHpaMnwa_MeWwcT6oivSusg_9xKb_NHYXccKtbensa-VQbafO-f-_vGKz0Rqc7353O3OBHQJ0xZk6P2xw5rLe1h-0_OqVg9-0KIl-dDBLVl6atUFhdJiNjfuQMSM2v7NuxsuRzt5eaEJMQmJbUXTp5mopYOuRNulLAkeBkjpd-uIln2eGa8glT20IbbhS68ftO1_8rg5hs-PjCx-IwA5xQ-eoLGLD-4cPXNcxGwZow0U48Mszw",
    "comment_data": {
      "comment": "Good song, inspirational and soothing",
      "videoId": 22,
      "seriesId": 15,
      "churchId": 27
    }
}
"""

main_backend_base_url = "https://uat.gospeltube.tv"
post_comment_endpoint = "/api/v1/user/videos/comment"


def save_comment_in_database(topic, data_string):
    """Save the message in the Databsse on GTube's main backend."""
    print(f"Saving comment . . .", flush=True)
    try:
        print(f"Extracting comment properties. . .", flush=True)
        dataJson =  json.loads(data_string)
        comment_data = dataJson.get('comment_data')
        bearer_token = dataJson.get('bearer_token')

        print(f"Saving comment . . . \n topic: {topic} \n comment_data: {comment_data} \n bearer_token: {bearer_token}", flush=True)
        
        # Call endpoint to save comment on the Main Backend
        data = json.dumps(comment_data)
        bearer_token = bearer_token.strip()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}",
        }

        endpoint = main_backend_base_url + post_comment_endpoint
        response = requests.post(
            endpoint,
            json = data,
            headers = headers,
        )
        print(f"Save comment response: {response}", flush=True)
        print("", flush=True)
    
    except Exception as error:
        print("Error occured: ", error)


class WebSocketHandler:
    """Handles multiple WebSocket connections with FastAPI."""

    def __init__(self):
        self.active_connections = {}  # Dictionary to store clients per topic

    async def connect(self, websocket: WebSocket, topic: str):
        """Accept a WebSocket connection and register it under a topic."""
        await websocket.accept()
        if topic not in self.active_connections:
            self.active_connections[topic] = []
        self.active_connections[topic].append(websocket)
        print(f"Client connected to topic: {topic}")

    def disconnect(self, websocket: WebSocket, topic: str):
        """Handle client disconnection and cleanup."""
        if (
            topic in self.active_connections
            and websocket in self.active_connections[topic]
        ):
            self.active_connections[topic].remove(websocket)
            if not self.active_connections[topic]:  # Remove empty topics
                del self.active_connections[topic]
        print(f"Client disconnected from topic: {topic}")

    async def send_message(self, topic: str, message: str):
        """Broadcast a message to all clients subscribed to a topic."""

        # Save message to GTube Main Database 
        print("Save comment and broadcast", flush=True)
        save_comment_in_database(topic, message)
        if topic in self.active_connections:
            for connection in self.active_connections[topic]:
                await connection.send_text(json.dumps({"broadcast": message}))
