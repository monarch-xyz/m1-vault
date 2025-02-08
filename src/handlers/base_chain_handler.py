from .base_handler import BaseHandler
from models.events import EventType
from utils.logger import LogService
from utils.market import get_vault_allocations, MarketInfo
import asyncio
from typing import Dict

class BaseChainEventHandler(BaseHandler):
    def __init__(self, agent, logger: LogService):
        super().__init__(agent)
        self.logger = logger
        self.tracked_markets: Dict[str, MarketInfo] = {}  # market_id -> MarketInfo
        
        # Initialize tracked markets
        asyncio.create_task(self._init_tracked_markets())
    
    async def _init_tracked_markets(self):
        """Initialize the list of markets we want to track"""
        try:
            market_infos = await get_vault_allocations()
            self.tracked_markets = {
                m.market_id: m for m in market_infos
            }
            
            print(f"Initialized tracking for {len(self.tracked_markets)} markets:")
            for market in market_infos:
                print(f"- {market.display_name} ({market.market_id})")

        except Exception as e:
            await self.logger.error("ChainHandler Init", str(e))

    @property
    def subscribes_to(self):
        return [EventType.CHAIN_EVENT]

    async def handle(self, event):
        # Skip if we haven't initialized our market list yet
        if not self.tracked_markets:
            return
            
        print('Event to handle: ', event)

        try:
            # Extract market_id from the event
            market_id = event.data.get('market_id')
            
            # Only process events for markets we care about
            if market_id in self.tracked_markets:
                market = self.tracked_markets[market_id]

                # only handle morpho_blue event, with asset > 100000

                await self.logger.think("Chain Event", {
                    "type": 'tracked_market_event',
                    "thought": f"Onchain event: {event.data.evm_event} event for {market.display_name}",
                    "market": {
                        "id": market_id,
                        "name": market.display_name,
                        "loan": market.loan_symbol,
                        "collateral": market.collateral_symbol,
                        "lltv": market.lltv
                    },
                    "data": {
                        "tx_hash": event.data.get('tx_hash'),
                        "caller": event.data.get('caller'),
                        "assets": event.data.get('assets'),
                        "shares": event.data.get('shares')
                    }
                })
                
        except Exception as e:
            await self.logger.error("ChainHandler", str(e))