from .base_handler import BaseHandler
from models.events import EventType
from utils.market import MarketInfo, get_vault_markets
from utils.supabase import SupabaseClient
from utils.activity_types import (
    MB_DEPOSIT_DETECTED, MB_WITHDRAWAL_DETECTED, 
    MB_BORROW_DETECTED, MB_REPAY_DETECTED
)
import asyncio
from typing import Dict
import logging

# Get the standard Python logger
logger = logging.getLogger(__name__)


class BaseChainEventHandler(BaseHandler):
    """
    We process all on-chain events, and store them in Supabase
    """

    def __init__(self, agent):
        super().__init__(agent)
        self.tracked_markets: Dict[str, MarketInfo] = {}  # market_id -> MarketInfo
        
        # Initialize tracked markets
        asyncio.create_task(self._init_tracked_markets())
    
    def _normalize_market_id(self, market_id: str) -> str:
        """Normalize market ID by removing '0x' prefix if present"""
        return market_id.lower().replace('0x', '')
    
    async def _init_tracked_markets(self):
        """Initialize the list of markets we want to track"""
        try:
            market_infos = await get_vault_markets()
            # Store markets with normalized IDs
            self.tracked_markets = {
                self._normalize_market_id(m.market_id): m 
                for m in market_infos
            }
            
            logger.info(f"Initialized tracking for {len(self.tracked_markets)} markets:")
            for market in market_infos:
                logger.info(f"- {market.display_name} ({market.market_id})")

        except Exception as e:
            logger.error(f"ChainHandler Init: {str(e)}")

    @property
    def subscribes_to(self):
        return [EventType.CHAIN_EVENT]

    async def handle(self, event):
        # Skip if we haven't initialized our market list yet
        if not self.tracked_markets:
            return

        try:
            # Skip vault events for now
            if event.data.get('source') == "morpho_vault":
                return

            # Extract and normalize market_id from the event
            raw_market_id = event.data.get('market_id')

            if not raw_market_id:
                return
                
            market_id = self._normalize_market_id(raw_market_id)
            
            # Only process events for markets we care about
            if market_id not in self.tracked_markets:
                return
            
            try:
                assets = int(event.data.get('assets', '0'))
                if assets < 10_000000:  # Skip small transactions
                    return
            except ValueError:
                return

            event_data = {
                "market": market_id,
                "event": event.data.get('evm_event'),
                "amount": assets,
                "data": {
                    "tx_hash": event.data.get('tx_hash'),
                    "caller": event.data.get('caller'),
                    "assets": event.data.get('assets'),
                    "shares": event.data.get('shares')
                }
            }

            # Store event in Supabase
            await SupabaseClient.store_onchain_events(event_data)
            
            # Broadcast activity based on event type
            await self._broadcast_morpho_blue_activity(event.data, market_id, assets)
                
        except Exception as e:
            logger.error(f"ChainHandler: {str(e)}")
    
    async def _broadcast_morpho_blue_activity(self, event_data, market_id, assets):
        """Broadcast activity for Morpho Blue events"""
        event_type = event_data.get('evm_event', '')
        
        # Map event type to activity type
        activity_type = None
        if event_type == 'supply':
            activity_type = MB_DEPOSIT_DETECTED
        elif event_type == 'withdraw':
            activity_type = MB_WITHDRAWAL_DETECTED
        elif event_type == 'borrow':
            activity_type = MB_BORROW_DETECTED
        elif event_type == 'repay':
            activity_type = MB_REPAY_DETECTED
        else:
            return  # Unsupported event type
        
        # Get market info for display name
        market_info = self.tracked_markets.get(market_id)
        
        # Broadcast activity
        await self.agent.broadcast_activity(activity_type, {
            "market_id": market_id,
            "tx_hash": event_data.get('tx_hash'),
            "sender": event_data.get('caller', ''),
            "amount": assets / 1e6,  # Convert to USDC units
            "timestamp": event_data.get('timestamp', 0)
        })