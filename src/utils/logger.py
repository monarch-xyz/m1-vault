from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, WebSocket
from enum import Enum
import json
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class LogCategory(Enum):
    EVENT = "event"
    THINK = "think"
    SPEAK = "speak"
    MEMORY = "memory"
    ACTION = "action"
    ERROR = "error"

class Logger:
    def __init__(self, websocket: Optional[WebSocket] = None):
        self.websocket = websocket
        self._logger = logging.getLogger("agent")
    
    async def _log(self, category: LogCategory, topic: str, details: Any):
        """Internal method to handle logging"""
        log_entry = {
            "category": category.value,
            "topic": topic,
            "details": details if isinstance(details, str) else json.dumps(details),
            "timestamp": datetime.now().isoformat()
        }
        
        # Always log to console
        self._logger.info(f"[{category.value}] {topic}: {details}")
        
        # If websocket is connected, send to frontend
        if self.websocket and not self.websocket.client_state.DISCONNECTED:
            try:
                await self.websocket.send_json(log_entry)
            except Exception as e:
                self._logger.error(f"Failed to send log to websocket: {str(e)}")

    async def event(self, topic: str, details: Any):
        """Log external event triggered, and received by our listeners"""
        await self._log(LogCategory.EVENT, topic, details)

    async def think(self, topic: str, details: Any):
        """Log thought process"""
        await self._log(LogCategory.THINK, topic, details)
    
    async def speak(self, topic: str, message: str):
        """Log outgoing messages"""
        await self._log(LogCategory.SPEAK, topic, message)
    
    async def memory(self, topic: str, data: Any):
        """Log memory operations"""
        await self._log(LogCategory.MEMORY, topic, data)
    
    async def action(self, topic: str, details: Any):
        """Log actions taken"""
        await self._log(LogCategory.ACTION, topic, details)
    
    async def error(self, topic: str, error: Exception):
        """Log errors"""
        await self._log(LogCategory.ERROR, topic, str(error))

# FastAPI app for websocket connection
app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger = Logger(websocket)
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # You could handle incoming commands here if needed
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        print("WebSocket connection closed")

if __name__ == "__main__":
    asyncio.run(main())