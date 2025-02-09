import asyncio
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler
from utils.logger import logger, start_log_server
from aiohttp import web

async def healthcheck(request):
    return web.Response(text="OK")

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
        app = web.Application()
        app.add_routes([web.get('/health', healthcheck)])
        
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