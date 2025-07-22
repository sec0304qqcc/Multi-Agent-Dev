"""
Message Bus for Agent Communication

This module provides Redis-based pub/sub messaging for inter-agent communication
and task coordination in the Multi-Agent Development Platform.
"""

import json
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel, Field

from ..config.settings import settings


class MessageType(str, Enum):
    """Message types for agent communication"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_UPDATE = "task_update"
    AGENT_STATUS = "agent_status"
    SYSTEM_ALERT = "system_alert"
    COORDINATION = "coordination"


class Message(BaseModel):
    """Standardized message format for agent communication"""
    id: str = Field(default_factory=lambda: f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    type: MessageType
    sender_id: str
    recipient_id: Optional[str] = None  # None for broadcast messages
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # For request/response tracking
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest, 10=lowest
    expires_at: Optional[datetime] = None


class MessageHandler:
    """Base class for message handlers"""
    
    def __init__(self, handler_id: str):
        self.handler_id = handler_id
        self.logger = logging.getLogger(f"message_handler.{handler_id}")
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming message and optionally return a response"""
        raise NotImplementedError


class MessageBus:
    """Redis-based message bus for agent communication"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.logger = logging.getLogger("message_bus")
        self.handlers: Dict[str, MessageHandler] = {}
        self.subscriptions: Dict[str, List[str]] = {}  # channel -> handler_ids
        self.running = False
        self.listener_tasks: List[asyncio.Task] = []
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Connected to Redis message bus")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis and cleanup"""
        self.running = False
        
        # Cancel listener tasks
        for task in self.listener_tasks:
            task.cancel()
        
        if self.listener_tasks:
            await asyncio.gather(*self.listener_tasks, return_exceptions=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Disconnected from Redis message bus")
    
    async def publish(self, channel: str, message: Message) -> int:
        """
        Publish a message to a channel
        
        Args:
            channel: Channel name to publish to
            message: Message to publish
            
        Returns:
            int: Number of subscribers that received the message
        """
        if not self.redis_client:
            raise RuntimeError("Message bus not connected")
        
        try:
            message_json = message.json()
            result = await self.redis_client.publish(channel, message_json)
            
            self.logger.debug(
                f"Published message {message.id} to channel {channel}, "
                f"delivered to {result} subscribers"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to publish message to {channel}: {e}")
            raise
    
    async def subscribe(self, channel: str, handler_id: str) -> None:
        """
        Subscribe a handler to a channel
        
        Args:
            channel: Channel name to subscribe to
            handler_id: ID of the message handler
        """
        if handler_id not in self.handlers:
            raise ValueError(f"Handler {handler_id} not registered")
        
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        
        if handler_id not in self.subscriptions[channel]:
            self.subscriptions[channel].append(handler_id)
            
            # Start listener if this is the first subscription to this channel
            if len(self.subscriptions[channel]) == 1:
                task = asyncio.create_task(self._listen_to_channel(channel))
                self.listener_tasks.append(task)
            
            self.logger.info(f"Handler {handler_id} subscribed to channel {channel}")
    
    async def unsubscribe(self, channel: str, handler_id: str) -> None:
        """
        Unsubscribe a handler from a channel
        
        Args:
            channel: Channel name to unsubscribe from
            handler_id: ID of the message handler
        """
        if channel in self.subscriptions and handler_id in self.subscriptions[channel]:
            self.subscriptions[channel].remove(handler_id)
            
            # If no more handlers for this channel, stop the listener
            if not self.subscriptions[channel]:
                del self.subscriptions[channel]
                # Cancel corresponding listener task
                for task in self.listener_tasks:
                    if not task.done() and channel in str(task):
                        task.cancel()
                        break
            
            self.logger.info(f"Handler {handler_id} unsubscribed from channel {channel}")
    
    def register_handler(self, handler: MessageHandler) -> None:
        """Register a message handler"""
        self.handlers[handler.handler_id] = handler
        self.logger.info(f"Registered message handler {handler.handler_id}")
    
    def unregister_handler(self, handler_id: str) -> None:
        """Unregister a message handler"""
        if handler_id in self.handlers:
            # Unsubscribe from all channels
            channels_to_remove = []
            for channel, handler_ids in self.subscriptions.items():
                if handler_id in handler_ids:
                    channels_to_remove.append(channel)
            
            for channel in channels_to_remove:
                asyncio.create_task(self.unsubscribe(channel, handler_id))
            
            del self.handlers[handler_id]
            self.logger.info(f"Unregistered message handler {handler_id}")
    
    async def _listen_to_channel(self, channel: str) -> None:
        """Listen to a specific channel and dispatch messages to handlers"""
        if not self.redis_client:
            return
        
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            
            self.logger.info(f"Started listening to channel {channel}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse message
                        msg_data = json.loads(message['data'])
                        msg = Message(**msg_data)
                        
                        # Dispatch to all subscribed handlers
                        if channel in self.subscriptions:
                            tasks = []
                            for handler_id in self.subscriptions[channel]:
                                if handler_id in self.handlers:
                                    handler = self.handlers[handler_id]
                                    tasks.append(
                                        asyncio.create_task(
                                            self._handle_message_safely(handler, msg)
                                        )
                                    )
                            
                            if tasks:
                                await asyncio.gather(*tasks, return_exceptions=True)
                    
                    except Exception as e:
                        self.logger.error(f"Error processing message from {channel}: {e}")
        
        except asyncio.CancelledError:
            self.logger.info(f"Channel listener for {channel} cancelled")
        except Exception as e:
            self.logger.error(f"Error in channel listener for {channel}: {e}")
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except:
                pass
    
    async def _handle_message_safely(self, handler: MessageHandler, message: Message) -> None:
        """Safely handle a message with error handling"""
        try:
            response = await handler.handle_message(message)
            
            # If handler returns a response, publish it
            if response and message.sender_id:
                response_channel = f"agent_{message.sender_id}_responses"
                await self.publish(response_channel, response)
        
        except Exception as e:
            self.logger.error(
                f"Handler {handler.handler_id} failed to process message {message.id}: {e}"
            )
    
    async def send_message(
        self,
        sender_id: str,
        recipient_id: Optional[str],
        message_type: MessageType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: int = 5
    ) -> str:
        """
        Send a message to a specific agent or broadcast
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the recipient agent (None for broadcast)
            message_type: Type of message
            payload: Message payload
            correlation_id: Optional correlation ID for request/response
            priority: Message priority (1=highest, 10=lowest)
            
        Returns:
            str: Message ID
        """
        message = Message(
            type=message_type,
            sender_id=sender_id,
            recipient_id=recipient_id,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority
        )
        
        # Determine channel
        if recipient_id:
            channel = f"agent_{recipient_id}"
        else:
            channel = "broadcast"
        
        await self.publish(channel, message)
        return message.id
    
    async def request_response(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[Message]:
        """
        Send a message and wait for a response
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the recipient agent
            message_type: Type of message
            payload: Message payload
            timeout: Timeout in seconds
            
        Returns:
            Optional[Message]: Response message or None if timeout
        """
        correlation_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Subscribe to response channel temporarily
        response_channel = f"agent_{sender_id}_responses"
        response_handler = ResponseHandler(correlation_id)
        
        self.register_handler(response_handler)
        await self.subscribe(response_channel, response_handler.handler_id)
        
        try:
            # Send request
            await self.send_message(
                sender_id=sender_id,
                recipient_id=recipient_id,
                message_type=message_type,
                payload=payload,
                correlation_id=correlation_id
            )
            
            # Wait for response
            response = await asyncio.wait_for(
                response_handler.wait_for_response(),
                timeout=timeout
            )
            
            return response
        
        except asyncio.TimeoutError:
            self.logger.warning(
                f"Request from {sender_id} to {recipient_id} timed out after {timeout}s"
            )
            return None
        
        finally:
            # Cleanup
            await self.unsubscribe(response_channel, response_handler.handler_id)
            self.unregister_handler(response_handler.handler_id)


class ResponseHandler(MessageHandler):
    """Special handler for waiting for responses"""
    
    def __init__(self, correlation_id: str):
        super().__init__(f"response_handler_{correlation_id}")
        self.correlation_id = correlation_id
        self.response_event = asyncio.Event()
        self.response: Optional[Message] = None
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle response message"""
        if message.correlation_id == self.correlation_id:
            self.response = message
            self.response_event.set()
        return None
    
    async def wait_for_response(self) -> Optional[Message]:
        """Wait for the response"""
        await self.response_event.wait()
        return self.response


# Global message bus instance
message_bus = MessageBus()