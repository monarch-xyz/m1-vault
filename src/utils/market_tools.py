""" Tools for LangGraph """

from langchain_core.tools import tool
from typing import List
from dataclasses import dataclass
from .market_api import MorphoAPIClient, Market, VaultResponse
from .market import get_morpho_markets, get_vault_allocations_summary

@tool
async def fetch_all_morpho_markets() -> str:
    """Fetch and format all Morpho Blue markets"""
    try:
        markets = await get_morpho_markets()
        response = ["Available Morpho Markets:"]
        for market in markets:
            response.append(
                f"\n- {market.collateralAsset.symbol}-{market.loanAsset.symbol}"
                f"\n  TVL: ${market.state.supplyAssetsUsd:,.2f}"
                f"\n  Utilization: {market.state.utilization * 100:.1f}%"
                f"\n  Supply APY: {market.state.supplyApy * 100:.2f}%"
                f"\n  Borrow APY: {market.state.borrowApy * 100:.2f}%"
            )
        
        return "\n".join(response)
    except Exception as e:
        return f"Error fetching markets: {str(e)}"

@tool
async def fetch_vault_market_status() -> str:
    """Get all of the markets and their allocations in the vault"""
    try:
        return await get_vault_allocations_summary()
    except Exception as e:
        return f"Error analyzing vault markets: {str(e)}"
