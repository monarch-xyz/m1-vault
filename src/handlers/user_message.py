from .base_handler import BaseHandler
from models.events import EventType

class UserMessageHandler(BaseHandler):

    @property
    def subscribes_to(self):
        return [EventType.USER_MESSAGE]

    async def handle(self, event):
        print(f"User message received: {event}") 