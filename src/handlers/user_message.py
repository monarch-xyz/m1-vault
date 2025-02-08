from .base_handler import BaseHandler
from models.events import EventType

class UserMessageHandler(BaseHandler):

    def __init__(self, logger):
        self.logger = logger

    @property
    def subscribes_to(self):
        return [EventType.USER_MESSAGE]

    async def handle(self, event):
        print(f"User message received: {event}") 
        await self.logger.think("User Message", event.data.text)
