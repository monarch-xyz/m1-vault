import asyncio
import os
from core.agent import Agent
from listeners.telegram_listener import TelegramListener
from listeners.onchain_listener import OnChainListener
from listeners.timer_listener import TimerListener
from handlers import AdminMessageHandler, UserMessageHandler, BaseChainEventHandler, PeriodicRiskHandler
from utils.supabase import SupabaseClient

async def main():
    # Initialize Supabase client
    SupabaseClient.init()

    # Initialize agent, initiate agent.event_bus
    agent = Agent()
    
    # Initialize components with logging
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
