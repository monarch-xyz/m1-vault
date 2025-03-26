from models.events import EventType, BaseEvent
from models.messages import TelegramMessage
from .base_handler import BaseHandler
from graphs.admin_react import create_admin_agent
from langchain_core.messages import HumanMessage
from utils import send_telegram_message_async
from utils.supabase import SupabaseClient
from utils.activity_types import MESSAGE_RECEIVED, IDLE
import logging

logger = logging.getLogger(__name__)

class AdminMessageHandler(BaseHandler):
    """ Entry point to handle admin messages (from telegram for now) """

    def __init__(self, agent):
        super().__init__(agent)
        self.llm = create_admin_agent(agent)

        logger.info("AdminMessageHandler initialized")

    @property
    def subscribes_to(self):
        return [EventType.TELEGRAM_MESSAGE]

    async def handle(self, event: BaseEvent):
        if self._is_admin_message(event):
            # Broadcast that we received a message
            await self.agent.broadcast_activity(MESSAGE_RECEIVED, {
                "sender": "admin",
                "timestamp": event.timestamp
            })

            await SupabaseClient.store_message({
                "text": event.data.text,
                "sender": "admin",
                "tx": None,
            })

            message = TelegramMessage.model_validate(event.data)
            response = await self._process_admin_command(message)

            await SupabaseClient.store_message({
                "text": response,
                "sender": "agent",
                "tx": None,
            })

            # send response back to the admin
            await send_telegram_message_async(message.chat_id, response)

            await self.agent.broadcast_activity(IDLE, {})

    def _is_admin_message(self, event):
        # Implement admin check logic
        return True

    async def _process_admin_command(self, message: TelegramMessage):
        # Process through the graph
        state = await self.llm.ainvoke({
            "messages": [HumanMessage(content=message.text)]
        }, config={"configurable": {"thread_id": "admin_chat"}})
        
        return state['messages'][-1].content

