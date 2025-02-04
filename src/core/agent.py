from typing import List
from abc import ABC, abstractmethod
from .event_bus import EventBus
from models.events import EventType

class Listener(ABC):
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
        # Start all components
        await self.event_bus.publish(EventType.SYSTEM_START)
    
    async def stop(self):
        self.running = False
        await self.event_bus.publish(EventType.SYSTEM_SHUTDOWN) 