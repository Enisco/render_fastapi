from fastapi import WebSocket
import asyncio
import json

import requests

"""
{
    "bearer_token": "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJzb2RlZXFlMDNAZ21haWwuY29tIiwicGVybWlzc2lvbnMiOiIiLCJyb2xlcyI6IlVTRVIiLCJpc3MiOiJzZWxmIiwiZXhwIjoxNzQ0NjkxNTQ0LCJpYXQiOjE3NDIwOTk1NDR9.MpDZyOIdEOOfAfBPXjwtWBSo9Fqk8ZLJ8nHEIM5nxSuSPh3CkOGSnaVyx-5oXFO9AVsGWR96Q-8RSNSA7O_edF-k7cFI05dt6zibpHpaMnwa_MeWwcT6oivSusg_9xKb_NHYXccKtbensa-VQbafO-f-_vGKz0Rqc7353O3OBHQJ0xZk6P2xw5rLe1h-0_OqVg9-0KIl-dDBLVl6atUFhdJiNjfuQMSM2v7NuxsuRzt5eaEJMQmJbUXTp5mopYOuRNulLAkeBkjpd-uIln2eGa8glT20IbbhS68ftO1_8rg5hs-PjCx-IwA5xQ-eoLGLD-4cPXNcxGwZow0U48Mszw",
    "comment": "Good song, inspirational and soothing",
    "videoId": 22,
    "seriesId": 15,
    "churchId": 27
}
"""

main_backend_base_url = "https://uat.gospeltube.tv"
post_comment_endpoint = "/api/v1/user/videos/comment"


def save_comment_in_database(bearer_token, data_json):
    """Save the message in the Databsse on GTube's main backend."""
    print(f"Saving comment . . .", flush=True)
    try:
        print(f"Saving comment . . . \n comment_data: {data_json} \n bearer_token: {bearer_token}", flush=True)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}",
        }

        endpoint = main_backend_base_url + post_comment_endpoint
        response = requests.post(
            endpoint,
            json = data_json,
            headers = headers,
        )
        print(f"Save comment response: {response.text}", flush=True)
        try:
            json_data = response.json()
            print(f"JSON Response: {json_data}", flush=True)
        except ValueError:
            print("Response is not in JSON format")

        print("Done saving comment", flush=True)
    
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

        print(f"Extracting comment properties. . .", flush=True)
        dataJson =  json.loads(message)
        comment_string = dataJson.get('comment')
        video_id = dataJson.get('videoId')
        series_id = dataJson.get('seriesId')
        church_id = dataJson.get('churchId')
        bearer_token = dataJson.get('bearer_token')

        # Extract comment data and create JSON object
        bearer_token = bearer_token.strip()
        comment_data = {
            "comment": comment_string,
            "videoId": video_id,
            "seriesId": series_id,
            "churchId": church_id
        }

        save_comment_in_database(bearer_token, comment_data)
        if topic in self.active_connections:
            for connection in self.active_connections[topic]:
                # await connection.send_text(json.dumps({"broadcast": message}))
                await connection.send_text(comment_data)
