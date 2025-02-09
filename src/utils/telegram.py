# Defined as function 

from telegram import Bot
from telegram.error import TelegramError
from typing import Optional
from config import Config
import logging

logger = logging.getLogger(__name__)

bot = Bot(Config.TELEGRAM_TOKEN)

async def send_telegram_message_async(
    chat_id: str,
    message: str,
    reply_to_message_id: Optional[int] = None
):
    try:
        if not chat_id or not message:
            raise ValueError("Both chat_id and message are required")
            
        # Show typing action
        await bot.send_chat_action(
            chat_id=int(chat_id),
            action="typing"
        )
        
        # Split long messages if needed (Telegram has a 4096 character limit)
        max_length = 4000  # Leave some room for formatting
        messages = [message[i:i+max_length] for i in range(0, len(message), max_length)]
        
        # Send each part
        for msg in messages:
            await bot.send_message(
                chat_id=int(chat_id),
                text=msg,
                reply_to_message_id=reply_to_message_id if messages[0] == msg else None
            )
            
        return f"Successfully sent {len(messages)} message(s) to chat {chat_id}"
        
    except TelegramError as e:
        error_msg = f"Telegram API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg
    except Exception as e:
        error_msg = f"Error sending Telegram message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg