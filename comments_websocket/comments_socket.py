
import json
import tornado
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
from fastapi import FastAPI
from starlette.websockets import WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """Handles WebSocket connections, allowing clients to subscribe to topics."""
    
    clients = {}  # Dictionary to store clients per topic

    def open(self, topic):
        """Handles a new client connection."""
        self.topic = topic
        if topic not in WebSocketHandler.clients:
            WebSocketHandler.clients[topic] = []
        WebSocketHandler.clients[topic].append(self)
        print(f"Client connected to topic: {topic}")
        self.write_message(json.dumps({"message": f"Connected to topic: {topic}"}))

    def on_message(self, message):
        """Handles incoming messages from a client."""
        print(f"Received on {self.topic}: {message}")

        # Acknowledge the message
        ack_message = json.dumps({"ack": f"Received '{message}' on topic '{self.topic}'"})
        self.write_message(ack_message)

        # Optional: Broadcast message to all clients in the topic
        self.broadcast(self.topic, message)

    def on_close(self):
        """Handles client disconnection."""
        if self.topic in WebSocketHandler.clients:
            WebSocketHandler.clients[self.topic].remove(self)
            if not WebSocketHandler.clients[self.topic]:  # Remove empty topics
                del WebSocketHandler.clients[self.topic]
        print(f"Client disconnected from topic: {self.topic}")

    @classmethod
    def broadcast(cls, topic, message):
        """Broadcast a message to all clients subscribed to a specific topic."""
        if topic in cls.clients:
            for client in cls.clients[topic]:
                try:
                    client.write_message(json.dumps({"broadcast": message}))
                except:
                    pass  # Ignore errors if a client is disconnected


def initialize_comments_socket():
    return tornado.web.Application([
        (r"/ws/([^/]+)", WebSocketHandler),
    ])
