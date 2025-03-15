from fastapi import WebSocket
import asyncio
import json

def save_comment_in_database(topic, data_string):
    """Save the message in the Databse on GTube backend."""
    print(f"Saving comment . . .")
    try:
        print(f"Extracting comment properties. . .")
        dataJson =  json.loads(data_string)
        message = dataJson.get('message')
        bearer_token = dataJson.get('bearer_token')

        print(f"Saving comment . . . \n topic: {topic} \n message: {message} \n bearer_token: {bearer_token}")
        # TODO: Call endpoint to save comment on the Main Backend
        # data = {"callId": call_id}
        # headers = {
        #     "Content-Type": "application/json",
        #     "Authorization": "Bearer YOUR_ACCESS_TOKEN",
        # }
        # response = requests.post(
        #     main_backend_base_url + start_live_session_endpoint,
        #     json=data,
        #     headers=headers,
        # )
        # print(f"Saving comment . . .: \n")
    
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
        print("Save comment and broadcast")
        save_comment_in_database(topic, message)
        if topic in self.active_connections:
            for connection in self.active_connections[topic]:
                await connection.send_text(json.dumps({"broadcast": message}))
