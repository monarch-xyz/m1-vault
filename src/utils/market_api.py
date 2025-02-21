# For Morpho API interactions
import aiohttp
from typing import Dict, List
from pydantic import BaseModel, Field
from .constants import (
    MORPHO_API_URL, 
    USDC_ADDRESS,
    MARKET_APY_QUERY,
    GET_MARKETS_QUERY,
    GET_VAULT_QUERY
)

class MarketParams(BaseModel):
    """Market parameters for Morpho markets."""
    loan_token: str = Field(..., description="Address of the loan token")
    collateral_token: str = Field(..., description="Address of the collateral token")
    oracle: str = Field(..., description="Address of the oracle")
    irm: str = Field(..., description="Address of the interest rate model")
    lltv: int = Field(..., description="Liquidation LTV (loan-to-value ratio) e.g. 770000000000000000 for 77%")

# API Response Types
class Asset(BaseModel):
    """Asset information from API"""
    address: str
    symbol: str
    decimals: int

class MarketState(BaseModel):
    """Market state from API"""
    borrowAssets: int
    supplyAssets: int
    borrowAssetsUsd: float
    supplyAssetsUsd: float
    utilization: float
    supplyApy: float
    borrowApy: float

class Market(BaseModel):
    """Market information from API"""
    id: str
    lltv: float
    uniqueKey: str
    irmAddress: str
    oracleAddress: str
    loanAsset: Asset
    collateralAsset: Asset | None
    state: MarketState

class MarketResponse(BaseModel):
    """Raw market response from API"""
    items: List[Market]

class MarketAllocation(BaseModel):
    """Market allocation from API"""
    market: Dict[str, str]  # Contains id and uniqueKey
    supplyAssets: int
    supplyCap: int

class VaultState(BaseModel):
    """Vault state from API"""
    allTimeApy: float
    apy: float
    totalAssets: int
    totalAssetsUsd: float
    allocation: List[MarketAllocation]

class VaultAsset(BaseModel):
    """Vault asset from API"""
    id: str
    decimals: int

class VaultResponse(BaseModel):
    """Raw vault response from API"""
    state: VaultState
    asset: VaultAsset

class MorphoAPIClient:
    """Client for Morpho API interactions"""
    
    @staticmethod
    async def get_market_apys(market_id: str) -> Dict:
        """Get market APYs"""
        async with aiohttp.ClientSession() as session:
            # prefix with 0x if not already
            if not market_id.startswith("0x"):
                market_id = "0x" + market_id
            try:
                async with session.post(
                    MORPHO_API_URL,
                    json={
                        "query": MARKET_APY_QUERY,
                        "variables": {"uniqueKey": market_id}
                    }
                ) as response:
                    data = await response.json()
                    market = data["data"]["markets"]["items"][0]
                    return {
                        'supply_apy': float(market["state"]["supplyApy"]) * 100,
                        'borrow_apy': float(market["state"]["borrowApy"]) * 100
                    }
            except Exception as e:
                print(f"Error fetching market APYs: {e}")
                return None

    @staticmethod
    async def get_all_markets() -> List[Market]:
        """Get all USDC markets"""
        async with aiohttp.ClientSession() as session:
            try:
                variables = {
                    "first": 100,
                    "where": {
                        "loanAssetAddress_in": [USDC_ADDRESS],
                        "whitelisted": True
                    }
                }
                
                async with session.post(
                    MORPHO_API_URL,
                    json={
                        "query": GET_MARKETS_QUERY,
                        "variables": variables
                    }
                ) as response:
                    data = await response.json()
                    if "errors" in data:
                        raise Exception(f"GraphQL errors: {data['errors']}")
                    
                    markets = [Market(**m) for m in data["data"]["markets"]["items"]]
                    return [m for m in markets if m.collateralAsset is not None]
                    
            except Exception as e:
                print(f"Error fetching markets: {e}")
                return []

    @staticmethod
    async def get_vault_data(vault_id: str) -> VaultResponse:
        """Get vault data"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    MORPHO_API_URL,
                    json={
                        "query": GET_VAULT_QUERY,
                        "variables": {"vaultId": vault_id}
                    }
                ) as response:
                    data = await response.json()
                    if "errors" in data:
                        raise Exception(f"GraphQL errors: {data['errors']}")
                    
                    return VaultResponse(**data["data"]["vaultByAddress"])
                    
            except Exception as e:
                print(f"Error fetching vault data: {e}")
                return None 


    @staticmethod
    async def get_market_params(market_ids: list[str]) -> list[MarketParams]:
        markets = await MorphoAPIClient.get_all_markets()
        
        market_params = []

        # for each market_id, find the market in the list of markets
        for market_id in market_ids:
            if not market_id.startswith("0x"):
                market_id = "0x" + market_id
            for market in markets:
                if market.uniqueKey == market_id:
                    market_params.append(MarketParams(
                        loan_token=market.loanAsset.address,
                        collateral_token=market.collateralAsset.address,
                        oracle=market.oracleAddress,
                        irm=market.irmAddress,
                        lltv=market.lltv
                    ))
        return market_params