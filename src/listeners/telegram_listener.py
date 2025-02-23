from core.agent import Listener
from models.events import EventType, BaseEvent
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
import os
import time
from models.messages import TelegramMessage


class TelegramListener(Listener):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.application = None
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    async def start(self):
        """Initialize and start the Telegram bot"""
        print("Starting telegram listener...")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
            
        self.application = Application.builder().token(self.bot_token).build()
        await self._setup_handlers()
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        print("Telegram bot started successfully!")

    async def _setup_handlers(self):
        """Configure message handlers"""
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_incoming_message
            )
        )

    async def _handle_incoming_message(self, update: Update, _) -> None:
        """Process incoming Telegram messages"""
        if not update.message or not update.message.text:
            return

        data = TelegramMessage(
            text=update.message.text,
            user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            username=update.effective_user.username,
        )

        event = BaseEvent(
            type=EventType.TELEGRAM_MESSAGE,
            data=data,
            source="telegram",
            timestamp=time.time()
        )

        await self.event_bus.publish(EventType.TELEGRAM_MESSAGE, event)

    async def stop(self):
        """Cleanly shutdown Telegram bot"""
        if self.application:
            print("Stopping telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            print("Telegram bot stopped!") 