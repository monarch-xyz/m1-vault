from models.events import EventType, BaseEvent
from models.messages import TelegramMessage, ChainMessage
from .base_handler import BaseHandler
from graphs.user_react import react_agent
from langchain_core.messages import HumanMessage
from utils import send_telegram_message_async
from utils.logger import LogService
from utils.supabase import SupabaseClient


class UserMessageHandler(BaseHandler):
    """Entry point to handle user messages (from telegram or onchain)"""

    def __init__(self, agent, logger: LogService):
        super().__init__(agent)
        self.llm = react_agent
        self.logger = logger
        print(f"UserMessageHandler initialized")

    @property
    def subscribes_to(self):
        return [EventType.USER_MESSAGE]

    async def handle(self, event: BaseEvent):
        try:
            # Log the incoming message
            if isinstance(event.data, ChainMessage):
                message_data = {
                    "text": event.data.text,
                    "sender": event.data.sender,
                    "tx": event.data.transaction_hash,
                }

                # Store message in Supabase
                await SupabaseClient.store_message(message_data)

                # log the message
                message_data.update({"from": "user"})
                await self.logger.conversation("User Message", message_data)

                # pass in a more detailed message to the agent, to access sender 
                message_text = "TEXT: {text} \n======\n USER_ID: {sender}".format(text=event.data.text, sender=event.data.sender)
                chat_id = event.data.sender

            else:
                print("Unknown message type!!!")
                return
            

            # Process through the user react graph
            config = {"configurable": {"thread_id": "user_public_chat"}}


            state = await self.llm.ainvoke({
                "messages": [
                    HumanMessage(content=message_text)
                ]
            }, config=config)
            
            response = state['messages'][-1].content

            # Log the agent's response
            await self.logger.conversation("Agent Response", {
                "from": "agent",
                "text": response
            })

        except Exception as e:
            await self.logger.error("UserMessageHandler", str(e))
