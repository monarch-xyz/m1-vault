import asyncio
import uvicorn
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler
from utils.logger import Logger, app
from contextlib import asynccontextmanager
from fastapi import FastAPI
# Create global logger instance
logger = Logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize agent and components
    agent = Agent(logger)
    
    # Initialize listeners
    listeners = [
        TelegramListener(agent.event_bus, logger),
        OnChainListener(agent.event_bus, logger)
    ]
    
    # Initialize handlers
    handlers = [
        AdminMessageHandler(agent, logger),
        UserMessageHandler(agent, logger),
        BaseChainEventHandler(agent, logger)
    ]
    
    # Start each listener explicitly
    for listener in listeners:
        await listener.start()
    
    # Start agent
    await agent.start()
    await logger.action("System", "Agent started successfully")
    
    try:
        yield
    finally:
        # Cleanup on shutdown
        for listener in listeners:
            await listener.stop()
        await agent.stop()
        await logger.action("System", "Agent stopped")

app.lifespan = lifespan

async def run_agent():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_agent()) 