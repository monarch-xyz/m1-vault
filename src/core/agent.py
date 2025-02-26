from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from .event_bus import EventBus
from models.events import EventType
from utils.websocket import WebSocketManager
from utils.activity_types import *  # Import all activity types
import time

class Listener(ABC):
    def __init__(self, event_bus):
        self.event_bus = event_bus
    
    @abstractmethod
    async def start(self):
        """Start the listener"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the listener"""
        pass

class Agent:
    def __init__(self):
        """Initialize agent with event bus"""
        self.event_bus = EventBus()
        self.running = False
        self._ws_manager: Optional[WebSocketManager] = None
    
    @property
    def ws_manager(self) -> Optional[WebSocketManager]:
        """Get WebSocket manager instance"""
        return self._ws_manager
    
    @ws_manager.setter
    def ws_manager(self, manager: WebSocketManager):
        """Set WebSocket manager instance"""
        self._ws_manager = manager
    
    async def broadcast_activity(self, activity_type: str, data: Dict[str, Any] = None):
        """Broadcast an activity to connected clients for monitoring"""
        if not data:
            data = {}
            
        activity = {
            "type": activity_type,
            "timestamp": time.time(),
            **data
        }
        
        if self._ws_manager:
            await self._ws_manager.broadcast_activity(activity)
    
    async def start(self):
        """Start the agent and notify connected clients"""
        self.running = True
        await self.event_bus.publish(EventType.SYSTEM_START)
        if self._ws_manager:
            await self.broadcast_activity(AGENT_STARTED, {
                "message": "Agent started successfully"
            })
    
    async def stop(self):
        """Stop the agent and notify connected clients"""
        self.running = False
        if self._ws_manager:
            await self.broadcast_activity(AGENT_STOPPING, {
                "message": "Agent shutting down"
            })
        await self.event_bus.publish(EventType.SYSTEM_SHUTDOWN)

__all__ = ['Agent', 'Listener'] 