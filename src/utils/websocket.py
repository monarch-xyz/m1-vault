from typing import Set
from aiohttp import web
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.connections: Set[web.WebSocketResponse] = set()
    
    async def connect(self, ws: web.WebSocketResponse):
        """Register new WebSocket connection"""
        self.connections.add(ws)
        logger.info(f"New WebSocket connection. Total connections: {len(self.connections)}")
    
    async def disconnect(self, ws: web.WebSocketResponse):
        """Remove WebSocket connection"""
        self.connections.remove(ws)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.connections)}")
    
    async def broadcast_activity(self, activity: dict):
        """Broadcast activity to all connections"""
        logger.info(f"Broadcasting activity: {activity['type']}")
        await self._broadcast("activity", activity)
    
    async def _broadcast(self, msg_type: str, data: dict):
        """Internal method to broadcast messages"""
        if not self.connections:
            logger.debug(f"No active connections to broadcast {msg_type} message")
            return
        
        message = {
            "type": msg_type,
            "data": data
        }
        
        logger.info(f"Broadcasting to {len(self.connections)} connections")
        dead_connections = set()
        
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except ConnectionResetError:
                logger.warning("Client disconnected during broadcast")
                dead_connections.add(ws)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                dead_connections.add(ws)
        
        # Cleanup dead connections
        for ws in dead_connections:
            await self.disconnect(ws)
    
    async def close_all_connections(self):
        """Close all active WebSocket connections"""
        if not self.connections:
            return
        
        logger.info(f"Closing {len(self.connections)} WebSocket connections")
        close_tasks = []
        
        for ws in list(self.connections):
            try:
                if not ws.closed:
                    close_tasks.append(ws.close(code=1001, message=b'Server shutdown'))
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.connections.clear()
        logger.info("All WebSocket connections closed") 