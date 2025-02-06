from models.events import EventType, BaseEvent
from models.messages import TelegramMessage
from .base_handler import BaseHandler
from graphs.admin_graph import create_admin_graph
from langchain_core.messages import HumanMessage
from utils import send_telegram_message_async


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
            response = await self._process_admin_command(message)

            # send response back to the admin
            await send_telegram_message_async(message.chat_id, response)

    def _is_admin_message(self, event):
        # Implement admin check logic
        return True

    async def _process_admin_command(self, message: TelegramMessage):
        # Process through the graph
        state = await self.graph.ainvoke({
            "messages": [HumanMessage(content=message.text)]
        })
        
        return state['messages'][-1].content

