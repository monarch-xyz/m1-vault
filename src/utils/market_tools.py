""" Tools for LangGraph """

from langchain_core.tools import tool
from typing import List
from dataclasses import dataclass
from .constants import VAULT_ADDRESS
from .market_api import MorphoAPIClient, Market, VaultResponse
from .market import get_morpho_markets

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
    """Fetch and format vault market status"""
    try:
        # Get vault and market data
        vault = await MorphoAPIClient.get_vault_data(VAULT_ADDRESS)
        markets = await get_morpho_markets()
        
        # Process data
        approved_market_ids = {alloc.market["id"] for alloc in vault.state.allocation}
        approved_markets = [m for m in markets if m.id in approved_market_ids]
        other_markets = [m for m in markets if m.id not in approved_market_ids]
        
        # Format response
        response = [
            f"Vault Analysis (${vault.state.totalAssetsUsd:,.2f} TVL)",
            f"Current APY: {vault.state.apy * 100:.2f}%",
            f"All-time APY: {vault.state.allTimeApy * 100:.2f}%\n"
        ]
        
        # Format approved markets
        response.append("\n🟢 Approved Markets (Can reallocate):")
        for market in approved_markets:
            allocation = next(a for a in vault.state.allocation if a.market["id"] == market.id)
            response.extend([
                f"\n- {market.collateralAsset.symbol}-{market.loanAsset.symbol} ({market.id})",
                f"  Current Supply: {allocation.supplyAssets/1e6:,.2f} USDC",
                f"  Supply Cap: {allocation.supplyCap/1e6:,.2f} USDC",
                f"  APY: {market.state.supplyApy * 100:.2f}%"
            ])
            
        return "\n".join(response)
    except Exception as e:
        return f"Error analyzing vault markets: {str(e)}"
