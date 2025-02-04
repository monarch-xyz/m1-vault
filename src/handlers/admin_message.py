from models.events import EventType
from .base_handler import BaseHandler

class AdminMessageHandler(BaseHandler):
    @property
    def subscribes_to(self):
        return [EventType.TELEGRAM_MESSAGE]

    async def handle(self, event):
        if self._is_admin_message(event):
            await self._process_admin_command(event.data)

    def _is_admin_message(self, event):
        # Implement admin check logic
        return True

    async def _process_admin_command(self, data):
        print(f"Admin message received: {data}") 