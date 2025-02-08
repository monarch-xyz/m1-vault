import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from aiohttp import web
import json

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('httpx').setLevel(logging.WARNING)

class LogCategory:
    EVENT = "event"
    THINK = "think"
    CONVERSATION = "conversation"
    MEMORY = "memory"
    ACTION = "action"
    ERROR = "error"

class LogService:
    def __init__(self):
        self.websocket_connections = set()
        self.logger = logging.getLogger("agent")
        self.logger.setLevel(logging.INFO)
        
        # Configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)

    async def log(self, category: str, topic: str, details: Any):
        """Core logging method"""
        log_entry = {
            "category": category,
            "topic": topic,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log to console
        self.logger.log(
            logging.ERROR if category == LogCategory.ERROR else logging.INFO,
            f"[{category}] {topic}: {details}"
        )
        
        # Broadcast to websockets
        await self.broadcast(log_entry)

    async def broadcast(self, message: Dict):
        """Send message to all connected websockets"""
        for ws in set(self.websocket_connections):
            try:
                await ws.send_json(message)
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
                self.websocket_connections.discard(ws)

    async def websocket_handler(self, request):
        """Handle incoming WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websocket_connections.add(ws)
        
        try:
            async for msg in ws:
                # Handle incoming messages if needed
                pass
        finally:
            self.websocket_connections.remove(ws)
        
        return ws

    # Add category-specific methods
    async def action(self, topic: str, details: Any):
        """Log an action taken by the system"""
        await self.log(LogCategory.ACTION, topic, details)

    async def think(self, topic: str, details: Any):
        """Log cognitive processing or decision making"""
        await self.log(LogCategory.THINK, topic, details)

    async def memory(self, topic: str, details: Any):
        """Log memory-related operations"""
        await self.log(LogCategory.MEMORY, topic, details)

    async def conversation(self, topic: str, details: Any):
        """Log output generation or communication"""
        await self.log(LogCategory.CONVERSATION, topic, details)

    async def error(self, topic: str, details: Any):
        """Log error conditions"""
        await self.log(LogCategory.ERROR, topic, details)

    async def event(self, topic: str, details: Any):
        """Log events"""
        await self.log(LogCategory.EVENT, topic, details)

# Singleton instance
logger = LogService()

# FastAPI-independent WebSocket setup
async def start_log_server():
    app = web.Application()
    app.add_routes([web.get('/ws', logger.websocket_handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    return runner, site

# Add module-level convenience functions
async def log_action(topic: str, details: Any):
    await logger.action(topic, details)

async def log_think(topic: str, details: Any):
    await logger.think(topic, details)

async def log_memory(topic: str, details: Any):
    await logger.memory(topic, details)

async def log_conversation(topic: str, details: Any):
    await logger.conversation(topic, details)

async def log_error(topic: str, details: Any):
    await logger.error(topic, details)

if __name__ == "__main__":
    asyncio.run(main())