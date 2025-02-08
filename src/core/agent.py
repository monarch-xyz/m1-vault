from typing import List
from abc import ABC, abstractmethod
from .event_bus import EventBus
from models.events import EventType
from utils.logger import LogService

class Listener(ABC):
    def __init__(self, event_bus, logger: LogService):
        self.event_bus = event_bus
        self.logger = logger
    
    @abstractmethod
    async def start(self):
        pass
    
    @abstractmethod
    async def stop(self):
        pass

class Agent:
    def __init__(self, logger: LogService):
        self.event_bus = EventBus()
        self.running = False
        self.logger = logger
    
    async def start(self):
        self.running = True
        await self.logger.action("Agent", "Starting agent...")
        await self.event_bus.publish(EventType.SYSTEM_START)
    
    async def stop(self):
        self.running = False
        await self.logger.action("Agent", "Stopping agent...")
        await self.event_bus.publish(EventType.SYSTEM_SHUTDOWN) 