from core.agent import Listener
from models.events import EventType, BaseEvent

class TelegramListener(Listener):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.client = None

    async def start(self):
        # Initialize client
        await self._setup_handlers()

    async def _setup_handlers(self):
        pass
        # Example telegram setup
        # self.client.add_handler(MessageHandler(
        #     filters.TEXT,
        #     lambda update, ctx: self._on_message(update)
        # ))

    async def _on_message(self, message):
        event = BaseEvent(
            type=EventType.TELEGRAM_MESSAGE,
            data={"text": message.text},
            source="telegram"
        )
        await self.event_bus.publish(event)

    async def stop(self):
        # Cleanup telegram client
        pass
    
    async def _handle_message(self, message):
        await self.handler.handle(message) 