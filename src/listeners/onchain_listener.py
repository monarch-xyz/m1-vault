from typing import Dict
from core.agent import Listener
from handlers.base_handler import BaseHandler
from models.events import EventType, BaseEvent
import time
import asyncio
from web3 import Web3
from config import Config

class OnChainListener(Listener):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.web3 = None
    
    async def start(self):
        print(f"Starting onchain listener with RPC URL: {Config.CHAIN_RPC_URL}")
        self.web3 = Web3(Web3.HTTPProvider(Config.CHAIN_RPC_URL))
        asyncio.create_task(self._poll_loop())
    
    async def _poll_loop(self):
        while True:
            latest_block = self.web3.eth.block_number
            
            # Todo: actual event logic
            print(f"Latest block: {latest_block}")

            await asyncio.sleep(60)  # Poll every minute
    
    def _parse_event(self, raw_event) -> BaseEvent:
        # Implement event parsing logic
        return BaseEvent(
            type=EventType.USER_MESSAGE,
            data=raw_event,
            source="blockchain",
            timestamp=time.time()
        )

    async def stop(self):
        # TODO: Cleanup Web3 connection
        print("OnChain listener stopped") 