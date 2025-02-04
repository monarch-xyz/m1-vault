from abc import ABC, abstractmethod
from models.events import BaseEvent, EventType

class BaseHandler(ABC):
    def __init__(self, agent):
        self.agent = agent
        self._register_subscriptions()

    def _register_subscriptions(self):
        """Auto-register on init"""
        for event_type in self.subscribes_to:
            self.agent.event_bus.subscribe(event_type, self.handle)

    @property
    @abstractmethod
    def subscribes_to(self) -> list[EventType]:
        """List of EventTypes this handler cares about"""
        pass

    @abstractmethod
    async def handle(self, event: BaseEvent):
        """Handle an incoming event"""
        pass 