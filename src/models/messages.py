from pydantic import BaseModel
import time
from typing import Optional

class BaseMessage(BaseModel):
    text: str
    timestamp: float = time.time()

class TelegramMessage(BaseMessage):
    user_id: int
    chat_id: int
    username: str

class ChainMessage(BaseMessage):
    sender: str
    transaction_hash: str