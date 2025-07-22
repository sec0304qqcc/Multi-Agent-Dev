"""
WebSocket endpoints for real-time communication

This module provides WebSocket endpoints for real-time updates
on agent status, task progress, and system events.
"""

import json
import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ..config.settings import settings


logger = logging.getLogger("websocket")

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_subscriptions: Dict[WebSocket, List[str]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_subscriptions[websocket] = []
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.client_subscriptions:
            del self.client_subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific client"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str, channel: str = "general"):
        """Broadcast message to all connected clients subscribed to channel"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                # Check if client is subscribed to this channel
                if channel in self.client_subscriptions.get(connection, []) or channel == "general":
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_text(message)
                    else:
                        disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    def subscribe_client(self, websocket: WebSocket, channels: List[str]):
        """Subscribe client to specific channels"""
        if websocket in self.client_subscriptions:
            self.client_subscriptions[websocket].extend(channels)
            logger.info(f"Client subscribed to channels: {channels}")
    
    def unsubscribe_client(self, websocket: WebSocket, channels: List[str]):
        """Unsubscribe client from specific channels"""
        if websocket in self.client_subscriptions:
            for channel in channels:
                if channel in self.client_subscriptions[websocket]:
                    self.client_subscriptions[websocket].remove(channel)
            logger.info(f"Client unsubscribed from channels: {channels}")


# Create connection manager
manager = ConnectionManager()

# Create router
websocket_router = APIRouter()


@websocket_router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        welcome_message = {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to Multi-Agent Development Platform",
            "available_channels": [
                "agent_status",
                "task_updates", 
                "system_alerts",
                "code_generation",
                "code_review"
            ]
        }
        await manager.send_personal_message(json.dumps(welcome_message), websocket)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                error_response = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # Subscribe to channels
        channels = message.get("channels", [])
        manager.subscribe_client(websocket, channels)
        
        response = {
            "type": "subscription",
            "status": "subscribed",
            "channels": channels,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(response), websocket)
    
    elif message_type == "unsubscribe":
        # Unsubscribe from channels
        channels = message.get("channels", [])
        manager.unsubscribe_client(websocket, channels)
        
        response = {
            "type": "subscription",
            "status": "unsubscribed", 
            "channels": channels,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(response), websocket)
    
    elif message_type == "ping":
        # Respond to ping with pong
        response = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(response), websocket)
    
    elif message_type == "get_status":
        # Send current system status
        await send_system_status(websocket)
    
    else:
        # Unknown message type
        response = {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(response), websocket)


async def send_system_status(websocket: WebSocket):
    """Send current system status to client"""
    try:
        # This would integrate with actual agent status
        status = {
            "type": "system_status",
            "timestamp": datetime.now().isoformat(),
            "agents": {
                "developer": {
                    "status": "idle",
                    "current_tasks": 0,
                    "success_rate": 95.0
                },
                "reviewer": {
                    "status": "idle", 
                    "current_tasks": 0,
                    "success_rate": 98.0
                }
            },
            "system": {
                "uptime": "running",
                "message_bus": "connected",
                "total_tasks_completed": 0
            }
        }
        
        await manager.send_personal_message(json.dumps(status), websocket)
    
    except Exception as e:
        logger.error(f"Error sending system status: {e}")


# Utility functions for broadcasting updates
async def broadcast_agent_status_update(agent_id: str, status: Dict[str, Any]):
    """Broadcast agent status update to subscribed clients"""
    message = {
        "type": "agent_status_update",
        "agent_id": agent_id,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(json.dumps(message), "agent_status")


async def broadcast_task_update(task_id: str, agent_id: str, status: str, progress: float = None):
    """Broadcast task progress update to subscribed clients"""
    message = {
        "type": "task_update",
        "task_id": task_id,
        "agent_id": agent_id,
        "status": status,
        "progress": progress,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(json.dumps(message), "task_updates")


async def broadcast_system_alert(level: str, message: str, details: Dict[str, Any] = None):
    """Broadcast system alert to all clients"""
    alert = {
        "type": "system_alert",
        "level": level,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(json.dumps(alert), "system_alerts")


async def broadcast_code_generation_result(task_id: str, result: Dict[str, Any]):
    """Broadcast code generation result to subscribed clients"""
    message = {
        "type": "code_generation_result",
        "task_id": task_id,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(json.dumps(message), "code_generation")


async def broadcast_code_review_result(task_id: str, review: Dict[str, Any]):
    """Broadcast code review result to subscribed clients"""
    message = {
        "type": "code_review_result",
        "task_id": task_id,
        "review": review,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(json.dumps(message), "code_review")


# Background task to send periodic status updates
async def periodic_status_broadcast():
    """Send periodic status updates to connected clients"""
    while True:
        try:
            if len(manager.active_connections) > 0:
                status_message = {
                    "type": "periodic_status",
                    "timestamp": datetime.now().isoformat(),
                    "connected_clients": len(manager.active_connections),
                    "uptime": "running"
                }
                await manager.broadcast(json.dumps(status_message), "general")
            
            # Wait 30 seconds before next update
            await asyncio.sleep(30)
        
        except Exception as e:
            logger.error(f"Error in periodic status broadcast: {e}")
            await asyncio.sleep(30)


# Start background task (this would be started by the main application)
# asyncio.create_task(periodic_status_broadcast())