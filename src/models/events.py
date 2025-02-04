from enum import Enum
from dataclasses import dataclass
from typing import Optional

class EventType(Enum):
    TELEGRAM_MESSAGE = "telegram_message"
    USER_MESSAGE = "user_message"
    CHAIN_EVENT = "chain_event"
    SYSTEM_START = "system_start"
    SYSTEM_SHUTDOWN = "system_shutdown"

@dataclass
class BaseEvent:
    type: EventType
    data: dict
    source: str
    timestamp: float
    correlation_id: Optional[str] = None 