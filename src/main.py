import asyncio
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler

async def main():
    agent = Agent()
    
    # Initialize listeners
    listeners = [
        TelegramListener(agent.event_bus),
        OnChainListener(agent.event_bus)
    ]
    
    # Initialize handlers
    handlers = [
        AdminMessageHandler(agent),
        UserMessageHandler(agent),
        BaseChainEventHandler(agent)
    ]
    
    # Start each listener explicitly
    for listener in listeners:
        await listener.start()
    
    # Start agent (this will publish SYSTEM_START event)
    await agent.start()
    
    try:
        # Keep the main process running
        while agent.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # Stop all listeners before shutting down
        for listener in listeners:
            await listener.stop()
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 