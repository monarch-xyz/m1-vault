from .base_handler import BaseHandler
from models.events import EventType
from utils.logger import LogService

class UserMessageHandler(BaseHandler):

    def __init__(self, agent, logger: LogService):
        self.agent = agent
        self.logger = logger

    @property
    def subscribes_to(self):
        return [EventType.USER_MESSAGE]

    async def handle(self, event):
        print(f"User message received: {event}") 
        await self.logger.conversation("User Message", {
            "from": "user",
            "text": event.data.text
        })
