import asyncio
import os
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from listeners.timer_listener import TimerListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler, PeriodicRiskHandler
from utils.logger import logger, start_log_server
from utils.supabase import SupabaseClient
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
    app.add_routes([web.get('/', healthcheck)])
    app.add_routes([web.get('/health', healthcheck)])
    
    # Initialize logging WebSocket
    await start_log_server(app)
    
    return app

async def main():
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Initialize Supabase client
    SupabaseClient.init()
    
    # Get port from Railway environment
    port = int(os.getenv("PORT", "8000"))
    
    # Explicit host/port binding
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    
    print(f"✅ Server running on 0.0.0.0:{port}")
    
    # Initialize agent with logging capability
    agent = Agent(logger=logger)
    
    # Initialize components with logging
    listeners = [
        TelegramListener(agent.event_bus, logger),
        OnChainListener(agent.event_bus, logger),
        TimerListener(agent.event_bus, logger)
    ]
    
    handlers = [
        AdminMessageHandler(agent, logger),
        UserMessageHandler(agent, logger),
        BaseChainEventHandler(agent, logger),
        PeriodicRiskHandler(agent, logger)
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
