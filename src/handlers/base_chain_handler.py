from .base_handler import BaseHandler
from models.events import EventType

class BaseChainEventHandler(BaseHandler):
    def __init__(self, logger):
        self.logger = logger

    @property
    def subscribes_to(self):
        return [EventType.CHAIN_EVENT]

    async def handle(self, event):
        print(f"Chain event received: {event}") 
        await self.logger.think("Chain Event", event.data.text)