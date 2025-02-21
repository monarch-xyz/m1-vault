from langchain_core.tools import tool
from typing import List, TypedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict
from web3 import Web3

from .constants import VAULT_ADDRESS
from .market_api import MorphoAPIClient, Market, VaultResponse
from .market_db import get_market_operations
from .market_onchain import MarketReader

@dataclass
class MarketInfo:
    """Business logic representation of a market"""
    market_id: str  # uniqueKey
    loan_symbol: str
    collateral_symbol: str
    lltv: float
    
    @property
    def display_name(self) -> str:
        """Human readable market name with LLTV in percentage"""
        lltv_percentage = (self.lltv / 1e18) * 100
        return f"{self.loan_symbol}-{self.collateral_symbol} ({lltv_percentage:.0f}%)"

class MarketSnapshot(TypedDict):
    id: str
    supply: int
    borrow: int
    withdraw: int
    repay: int
    net_supply: int
    net_borrow: int
    total_supply: int
    total_borrow: int
    liquidity: int
    supply_apy: float
    borrow_apy: float

async def get_morpho_markets() -> List[Market]:
    """Get all Morpho markets"""
    return await MorphoAPIClient.get_all_markets()

async def get_vault_allocations() -> List[MarketInfo]:
    """Get formatted vault allocation info"""
    try:
        vault = await MorphoAPIClient.get_vault_data(VAULT_ADDRESS)
        markets = await get_morpho_markets()
        markets_by_id = {m.id: m for m in markets}
        
        market_infos = []
        for allocation in vault.state.allocation:
            market = markets_by_id.get(allocation.market["id"])
            if market:
                market_infos.append(MarketInfo(
                    market_id=allocation.market["uniqueKey"],
                    loan_symbol=market.loanAsset.symbol,
                    collateral_symbol=market.collateralAsset.symbol,
                    lltv=market.lltv
                ))
        
        return market_infos
    except Exception as e:
        print(f"Error getting vault allocations: {e}")
        return []


async def get_all_market_history_summary(web3: Web3, hours_ago: int = 1) -> List[MarketSnapshot]:
    """ Get a list of market snapshots with net flows over a period of time"""
    market_reader = MarketReader(web3)
    api_client = MorphoAPIClient()
    
    # Get operations from DB
    operations = await get_market_operations(hours_ago)
    if not operations:
        return []
    
    consolidated_data = []
    for market in operations:
        market_id = market['id']
        
        # Get on-chain stats
        stats = await market_reader.get_market_data(market_id)
        if not stats:
            continue
            
        # Get APYs from API
        apys = await api_client.get_market_apys(market_id)
        if not apys:
            continue
            
        # Calculate net movements
        net_supply = market['supply'] - market['withdraw']
        net_borrow = market['borrow'] - market['repay']
        
        snapshot = MarketSnapshot(
            id=market_id,
            supply=market['supply'],
            borrow=market['borrow'],
            withdraw=market['withdraw'],
            repay=market['repay'],
            net_supply=net_supply,
            net_borrow=net_borrow,
            total_supply=stats['supply_assets'],
            total_borrow=stats['borrow_assets'],
            liquidity=stats['liquidity'],
            supply_apy=apys['supply_apy'],
            borrow_apy=apys['borrow_apy']
        )
        
        consolidated_data.append(snapshot)
    
    return consolidated_data 