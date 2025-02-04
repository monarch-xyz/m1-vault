from models.events import EventType, BaseEvent
from models.messages import TelegramMessage
from .base_handler import BaseHandler
from graphs.admin_graph import create_admin_graph


class AdminMessageHandler(BaseHandler):
    """ Entry point to handle admin messages (from telegram for now) """

    def __init__(self, agent):
        super().__init__(agent)
        self.graph = create_admin_graph()

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
        # Process through the graph
        state = await self.graph.ainvoke({
            "message": message.text
        })
        
        print(f"Admin command processed: {state['response']}")
        
        