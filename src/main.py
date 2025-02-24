import asyncio
import os
from aiohttp import web
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from listeners.timer_listener import TimerListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler, PeriodicRiskHandler
from utils.supabase import SupabaseClient

async def healthcheck(request):
    """Simple healthcheck endpoint"""
    return web.Response(text="OK")

async def init_app():
    """Initialize web application with routes"""
    app = web.Application()
    
    # Add healthcheck routes
    app.router.add_get('/', healthcheck)
    app.router.add_get('/health', healthcheck)
    
    return app

async def start_web_server(port: int):
    """Start web server on specified port"""
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    
    print(f"✅ Server running on 0.0.0.0:{port}")
    return runner

async def main():
    try:
        # Initialize Supabase client
        SupabaseClient.init()

        # Start web server
        port = int(os.getenv("PORT", "8000"))
        runner = await start_web_server(port)

        # Initialize agent
        agent = Agent()
        
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
        print("\nShutting down...")
        await agent.stop()
        
    finally:
        # Cleanup
        for listener in listeners:
            await listener.stop()
        
        # Cleanup web server
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
