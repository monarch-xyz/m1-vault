from models.events import EventType, BaseEvent
from models.messages import TelegramMessage
from .base_handler import BaseHandler
from graphs.admin_react import react_agent
from langchain_core.messages import HumanMessage
from utils import send_telegram_message_async
from utils.logger import LogService

class AdminMessageHandler(BaseHandler):
    """ Entry point to handle admin messages (from telegram for now) """

    def __init__(self, agent, logger: LogService):
        super().__init__(agent)
        self.agent = react_agent
        self.logger = logger

        print(f"AdminMessageHandler initialized")

    @property
    def subscribes_to(self):
        return [EventType.TELEGRAM_MESSAGE]

    async def handle(self, event: BaseEvent):
        if self._is_admin_message(event):
            await self.logger.conversation("Admin Message", {
                "from": "admin",
                "text": event.data.text
            })

            message = TelegramMessage.model_validate(event.data)
            response = await self._process_admin_command(message)

            await self.logger.conversation("Agent Response", {
                "from": "agent",
                "text": response
            })

            # send response back to the admin
            await send_telegram_message_async(message.chat_id, response)

    def _is_admin_message(self, event):
        # Implement admin check logic
        return True

    async def _process_admin_command(self, message: TelegramMessage):
        # Process through the graph
        state = await self.agent.ainvoke({
            "messages": [HumanMessage(content=message.text)]
        })
        
        return state['messages'][-1].content

