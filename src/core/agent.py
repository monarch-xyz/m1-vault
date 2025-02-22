from typing import List
from abc import ABC, abstractmethod
from .event_bus import EventBus
from models.events import EventType
from utils.broadcaster import ws_client

class Listener(ABC):
    def __init__(self, event_bus):
        self.event_bus = event_bus
    
    @abstractmethod
    async def start(self):
        pass
    
    @abstractmethod
    async def stop(self):
        pass

class Agent:
    def __init__(self):
        self.event_bus = EventBus()
        self.running = False
    
    async def start(self):
        self.running = True
        await ws_client.broadcast_action("restart", "Agent restarted")
        await self.event_bus.publish(EventType.SYSTEM_START)
    
    async def stop(self):
        self.running = False
        await ws_client.broadcast_action("shutdown", "Agent stopped")
        await self.event_bus.publish(EventType.SYSTEM_SHUTDOWN)

__all__ = ['Agent', 'Listener'] 