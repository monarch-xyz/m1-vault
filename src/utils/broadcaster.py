import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from aiohttp import web
import json
import logging

# Get the standard Python logger
logger = logging.getLogger(__name__)

class MessageType:
    """Message types for different activities"""
    # Actions
    ACTION_DEPOSIT = "action:deposit"
    ACTION_WITHDRAW = "action:withdraw"
    ACTION_REALLOCATION = "action:reallocation"
    
    # Thoughts/Analysis
    THOUGHT_ANALYSIS = "thought:analysis"
    THOUGHT_STRATEGY = "thought:strategy"
    
    # Reports
    REPORT_DAILY = "report:daily"
    REPORT_WEEKLY = "report:weekly"
    
    # Chat
    CHAT_USER = "chat:user"
    CHAT_AGENT = "chat:agent"
    CHAT_ADMIN = "chat:admin"

class WebSocketBroadcaster:
    def __init__(self):
        self.websocket_connections = set()

    async def broadcast(self, message_type: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Broadcast message to all connected WebSocket clients"""
        message = {
            "type": message_type,
            "text": text,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata or {}
        }
        
        # Log the broadcast for debugging
        logger.debug(f"Broadcasting message: {message}")
        
        # Send to all connected clients
        for ws in set(self.websocket_connections):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
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

    # Action broadcasting methods
    async def broadcast_action(self, action_type: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Broadcast system actions with optional transaction metadata"""
        await self.broadcast(f"action:{action_type}", text, metadata)

    # Thought process broadcasting methods
    async def broadcast_thought(self, thought_type: str, text: str):
        """Broadcast agent's thought processes and analysis"""
        await self.broadcast(f"thought:{thought_type}", text)

    # Report broadcasting methods
    async def broadcast_report(self, report_type: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Broadcast system reports with optional metadata"""
        await self.broadcast(f"report:{report_type}", text, metadata)

    # Chat broadcasting methods
    async def broadcast_chat(self, sender_type: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Broadcast chat messages"""
        await self.broadcast(f"chat:{sender_type}", text, metadata)

# Singleton instance
ws_client = WebSocketBroadcaster()

async def start_websocket_server(app: web.Application):
    """Add WebSocket route to existing application"""
    app.add_routes([web.get('/ws', ws_client.websocket_handler)])

# Usage examples:
# await ws_client.broadcast_action("reallocation", "Reallocating 1000 USDC to AAVE", {"txHash": "0x123..."})
# await ws_client.broadcast_thought("analysis", "Market Analysis:\n- AAVE APY: 3.2% (↑0.2%)")
# await ws_client.broadcast_report("daily", "Daily Summary:\n- Total Value: 100,000 USDC")
# await ws_client.broadcast_chat("user", "Hello, how is the market today?", {"sender": "0x456..."}) 