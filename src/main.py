import asyncio
import os
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler
from utils.logger import logger, start_log_server
from aiohttp import web

async def healthcheck(request):
    return web.Response(text="OK")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    async for msg in ws:
        # Handle WebSocket messages here
        await ws.send_str(f"Received: {msg.data}")
    
    return ws

async def init_app():
    app = web.Application()
    app.add_routes([
        web.get('/health', healthcheck),
        web.get('/ws', websocket_handler)
    ])
    return app

async def main():
    # Start logging server first
    log_runner, log_site = await start_log_server()
    
    # Initialize agent with logging capability
    agent = Agent(logger=logger)
    
    # Initialize components with logging
    listeners = [
        TelegramListener(agent.event_bus, logger),
        OnChainListener(agent.event_bus, logger)
    ]
    
    handlers = [
        AdminMessageHandler(agent, logger),
        UserMessageHandler(agent, logger),
        BaseChainEventHandler(agent, logger)
    ]

    try:
        # Start listeners
        for listener in listeners:
            await listener.start()
        
        # Start agent
        await agent.start()
        
        # Add healthcheck endpoint
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Get port from environment with proper fallback
        port = int(os.getenv("PORT", "8000"))  # Default to 8000
        
        try:
            site = web.TCPSite(runner, host='0.0.0.0', port=port)
            await site.start()
            print(f"Server started on port {port}")
        except OSError as e:
            print(f"Failed to start server on port {port}: {e}")
            print(f"Try either:")
            print(f"1. Changing PORT environment variable (current: {port})")
            print(f"2. Killing process using port: lsof -i :{port} | awk")
            raise
        
        # Keep main loop running
        while agent.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        await agent.stop()
    finally:
        # Cleanup
        await log_site.stop()
        await log_runner.cleanup()
        for listener in listeners:
            await listener.stop()

if __name__ == "__main__":
    asyncio.run(main()) 