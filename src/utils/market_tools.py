""" Tools for LangGraph """

from langchain_core.tools import tool
from typing import List, Optional
from dataclasses import dataclass
from .market_api import MorphoAPIClient, Market, VaultResponse
from .market import get_morpho_markets, get_vault_allocations_summary
from utils.activity_types import MARKET_DATA_FETCHED, VAULT_DATA_FETCHED
import time

# Create versions of tools that can access the agent
def create_market_tools(agent):
    """Create market tools with access to the agent for broadcasting"""
    
    @tool
    async def fetch_all_morpho_markets() -> str:
        """Fetch and format all Morpho Blue markets"""
        try:
            # Broadcast that we're fetching market data
            if agent and agent.ws_manager:
                await agent.broadcast_activity(MARKET_DATA_FETCHED, {
                    "message": "Fetching all Morpho markets",
                    "source": "Morpho Blue API",
                    "timestamp": time.time()
                })
                
            markets = await get_morpho_markets()
            
            # Format the market data for readable output
            response = ["Available Morpho Markets:"]
            for market in markets:
                response.append(
                    f"\n- {market.collateralAsset.symbol}-{market.loanAsset.symbol}"
                    f"\n  TVL: ${market.state.supplyAssetsUsd:,.2f}"
                    f"\n  Utilization: {market.state.utilization * 100:.1f}%"
                    f"\n  Supply APY: {market.state.supplyApy * 100:.2f}%"
                    f"\n  Borrow APY: {market.state.borrowApy * 100:.2f}%"
                )
            
            result = "\n".join(response)
            
            # Broadcast a preview of the results
            if agent and agent.ws_manager:
                # Get a summary of the data for the broadcast
                market_count = len(markets)
                highest_apy = max([m.state.supplyApy for m in markets], default=0) * 100
                
                await agent.broadcast_activity(MARKET_DATA_FETCHED, {
                    "message": "Market data retrieved",
                    "market_count": market_count,
                    "highest_apy": f"{highest_apy:.2f}%",
                    "preview": result[:200] + "..." if len(result) > 200 else result,
                    "timestamp": time.time()
                })
            
            return result
        except Exception as e:
            if agent and agent.ws_manager:
                await agent.broadcast_activity(MARKET_DATA_FETCHED, {
                    "message": f"Error fetching markets: {str(e)}",
                    "error": True,
                    "timestamp": time.time()
                })
            return f"Error fetching markets: {str(e)}"

    @tool
    async def fetch_vault_market_status() -> str:
        """Get all of the markets and their allocations in the vault"""
        try:
            # Broadcast that we're fetching vault data
            if agent and agent.ws_manager:
                await agent.broadcast_activity(VAULT_DATA_FETCHED, {
                    "message": "Fetching vault allocations",
                    "source": "Vault API",
                    "timestamp": time.time()
                })
                
            result = await get_vault_allocations_summary()

            # Broadcast with more details
            if agent and agent.ws_manager:
                # Extract some meaningful data from the result for the broadcast
                allocation_preview = result[:200] + "..." if len(result) > 200 else result
                
                await agent.broadcast_activity(VAULT_DATA_FETCHED, {
                    "message": "Vault allocation data retrieved",
                    "preview": allocation_preview,
                    "timestamp": time.time()
                })
                
            return result
        except Exception as e:
            if agent and agent.ws_manager:
                await agent.broadcast_activity(VAULT_DATA_FETCHED, {
                    "message": f"Error analyzing vault markets: {str(e)}",
                    "error": True,
                    "timestamp": time.time()
                })
            return f"Error analyzing vault markets: {str(e)}"
            
    # Return the tools with access to the agent
    return [fetch_all_morpho_markets, fetch_vault_market_status]
