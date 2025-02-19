from .base_handler import BaseHandler
from models.events import EventType
from utils.logger import LogService
from utils.market import get_vault_allocations, MarketInfo
from utils.supabase import SupabaseClient
import asyncio
from typing import Dict

class BaseChainEventHandler(BaseHandler):
    def __init__(self, agent, logger: LogService):
        super().__init__(agent)
        self.logger = logger
        self.tracked_markets: Dict[str, MarketInfo] = {}  # market_id -> MarketInfo
        
        # Initialize tracked markets
        asyncio.create_task(self._init_tracked_markets())
    
    def _normalize_market_id(self, market_id: str) -> str:
        """Normalize market ID by removing '0x' prefix if present"""
        return market_id.lower().replace('0x', '')
    
    async def _init_tracked_markets(self):
        """Initialize the list of markets we want to track"""
        try:
            market_infos = await get_vault_allocations()
            # Store markets with normalized IDs
            self.tracked_markets = {
                self._normalize_market_id(m.market_id): m 
                for m in market_infos
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

        try:
            # Extract and normalize market_id from the event
            raw_market_id = event.data.get('market_id')
            if not raw_market_id:
                return
                
            market_id = self._normalize_market_id(raw_market_id)
            
            # Only process events for markets we care about
            if market_id in self.tracked_markets:
                market = self.tracked_markets[market_id]
                
                # only handle morpho_blue event, with asset > 100000
                if event.source == "morpho_blue":
                    try:
                        assets = int(event.data.get('assets', '0'))
                        if assets < 10_000000:  # Skip small transactions
                            return
                    except ValueError:
                        return

                formated_assets = f"{assets / 10**6:.2f} USDC"

                thought = {
                    "text": f"Onchain event: {event.data.get('evm_event')} event for {market.display_name}, {formated_assets} USDC"
                }

                event_data = {
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
                }
                
                # Store thought in Supabase
                await SupabaseClient.store_thoughts(thought)
                await SupabaseClient.store_onchain_events(event_data)

                # Log the event
                event_data.update({"type": "live_event"})
                await self.logger.think("Chain Event", event_data)
                
        except Exception as e:
            await self.logger.error("ChainHandler", str(e))