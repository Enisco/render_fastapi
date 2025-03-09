from fastapi import WebSocket
import asyncio
import json

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
        if topic in self.active_connections and websocket in self.active_connections[topic]:
            self.active_connections[topic].remove(websocket)
            if not self.active_connections[topic]:  # Remove empty topics
                del self.active_connections[topic]
        print(f"Client disconnected from topic: {topic}")

    async def send_message(self, topic: str, message: str):
        """Broadcast a message to all clients subscribed to a topic."""
        if topic in self.active_connections:
            for connection in self.active_connections[topic]:
                await connection.send_text(json.dumps({"broadcast": message}))

    async def save_comment_in_database(self, topic: str, message: str):
        """Save the message in the Databse on GTube backend."""
        try:
            if topic in self.active_connections:
                for connection in self.active_connections[topic]:
                    await connection.send_text(json.dumps({"broadcast": message}))

        except Exception as error:
            print("Error occured: ", error)
