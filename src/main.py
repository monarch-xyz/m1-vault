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
    
    # Add healthcheck route
    app.add_routes([web.get('/health', healthcheck)])
    
    # Initialize logging WebSocket
    await start_log_server(app)
    
    return app

async def main():
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", "8000"))
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    
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
        
        # Keep main loop running
        while agent.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        await agent.stop()
    finally:
        # Cleanup
        for listener in listeners:
            await listener.stop()

if __name__ == "__main__":
    asyncio.run(main()) 