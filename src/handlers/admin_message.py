from models.events import EventType, BaseEvent
from models.messages import TelegramMessage
from .base_handler import BaseHandler


class AdminMessageHandler(BaseHandler):
    @property
    def subscribes_to(self):
        return [EventType.TELEGRAM_MESSAGE]

    async def handle(self, event: BaseEvent):
        if self._is_admin_message(event):
            message = TelegramMessage.model_validate(event.data)
            await self._process_admin_command(message)

    def _is_admin_message(self, event):
        # Implement admin check logic
        return True

    async def _process_admin_command(self, message: TelegramMessage):
        print(f"Admin message received: {message}") 