import asyncio
import os
from aiohttp import web
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from listeners.timer_listener import TimerListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler, PeriodicRiskHandler
from utils.supabase import SupabaseClient
from utils.websocket import WebSocketManager
import logging

logger = logging.getLogger(__name__)

async def healthcheck(request):
    """Simple healthcheck endpoint"""
    return web.Response(text="OK")

async def websocket_handler(request):
    """Handle WebSocket connections"""
    # Get the WebSocket manager before any potential exceptions occur
    ws_manager = request.app['ws_manager']
    
    # Set WebSocket specific settings
    ws = web.WebSocketResponse(heartbeat=30)
    connection_prepared = False
    
    try:
        # Prepare must happen first before any other WebSocket operations
        await ws.prepare(request)
        connection_prepared = True
        
        # Register the new connection
        await ws_manager.connect(ws)
        
        # Process incoming messages
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                logger.info(f"Received message: {msg.data}")
            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f'WebSocket connection closed with exception {ws.exception()}')
                break
    except ConnectionResetError:
        logger.warning("Client disconnected abruptly")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Only attempt to clean up if the connection was successfully prepared
        if connection_prepared and ws in ws_manager.connections:
            await ws_manager.disconnect(ws)
    
    return ws

async def init_app():
    """Initialize web application with routes"""
    app = web.Application()
    
    # Initialize WebSocket manager
    ws_manager = WebSocketManager()
    app['ws_manager'] = ws_manager
    
    # Add routes
    app.router.add_get('/', healthcheck)
    app.router.add_get('/health', healthcheck)
    app.router.add_get('/ws', websocket_handler)
    
    return app

async def start_web_server(port: int):
    """Start web server on specified port"""
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    
    logger.info(f"✅ Server running on 0.0.0.0:{port}")
    return runner, app['ws_manager']

async def main():
    listeners = []
    runner = None
    agent = None
    
    try:
        # Initialize Supabase client
        SupabaseClient.init()

        # Start web server and get WebSocket manager
        port = int(os.getenv("PORT", "8000"))
        runner, ws_manager = await start_web_server(port)

        # Initialize agent with WebSocket manager
        agent = Agent()
        agent.ws_manager = ws_manager
        
        # Initialize components
        listeners = [
            TelegramListener(agent.event_bus),
            OnChainListener(agent.event_bus),
            TimerListener(agent.event_bus)
        ]
        
        handlers = [
            AdminMessageHandler(agent),
            UserMessageHandler(agent),
            BaseChainEventHandler(agent),
            PeriodicRiskHandler(agent)
        ]

        # Start listeners
        for listener in listeners:
            await listener.start()
        
        # Start agent
        await agent.start()
        
        # Keep main loop running
        while agent.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
    finally:
        # Simple sequence with proper WebSocket handling
        
        # 1. Stop the agent
        if agent and agent.running:
            logger.info("Stopping agent...")
            await agent.stop()
        
        # 2. Stop all listeners
        if listeners:
            logger.info("Stopping listeners...")
            for listener in listeners:
                await listener.stop()
        
        # 3. Close all WebSocket connections
        if runner and ws_manager:
            logger.info("Closing WebSocket connections...")
            await ws_manager.close_all_connections()
        
        # 4. Cleanup web server with timeout to prevent hanging
        if runner:
            logger.info("Stopping web server...")
            try:
                await asyncio.wait_for(runner.cleanup(), timeout=3)
            except asyncio.TimeoutError:
                logger.warning("Web server cleanup timed out")
        
        logger.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
