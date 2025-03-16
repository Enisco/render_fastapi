from fastapi import WebSocket
import asyncio
import json

import requests

"""
{
    "bearer_token": "tfgh456c86ggghhjkj",
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
    """Save the message in the Databse on GTube backend."""
    print(f"Saving comment . . .", flush=True)
    try:
        print(f"Extracting comment properties. . .", flush=True)
        dataJson =  json.loads(data_string)
        comment_data = dataJson.get('comment_data')
        bearer_token = dataJson.get('bearer_token')

        print(f"Saving comment . . . \n topic: {topic} \n comment_data: {comment_data} \n bearer_token: {bearer_token}", flush=True)
        
        # Call endpoint to save comment on the Main Backend
        data = json.loads(comment_data)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {bearer_token}",
        }

        endpoint = main_backend_base_url + post_comment_endpoint
        response = requests.post(
            endpoint,
            json = data,
            headers = headers,
        )
        print(f"Save comment response: {response}", flush=True)
    
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
