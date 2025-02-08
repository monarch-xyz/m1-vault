from .base_handler import BaseHandler
from models.events import EventType
from utils.logger import LogService

class BaseChainEventHandler(BaseHandler):
    def __init__(self, agent, logger: LogService):
        super().__init__(agent)
        self.logger = logger

    @property
    def subscribes_to(self):
        return [EventType.CHAIN_EVENT]

    async def handle(self, event):



        await self.logger.think("Chain Event", {
            "type": event["evm_event"],
            "thought": "I got a chain event",
            "data": "Not parsed for now"
        })