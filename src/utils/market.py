from langchain_core.tools import tool
from typing import Dict, List, Optional, Annotated
from pydantic import BaseModel
import aiohttp
import logging
from enum import Enum
from dataclasses import dataclass
from web3 import Web3
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# always use our vault
VAULT_ADDRESS = "0x346aac1e83239db6a6cb760e95e13258ad3d1a6d"

# GraphQL query
GET_MARKETS = """
    query getMarkets($first: Int, $where: MarketFilters) {
        markets(first: $first, where: $where) {
            items {
                id
                lltv
                uniqueKey
                oracleAddress
                irmAddress
                loanAsset {
                    address
                    symbol
                    decimals
                }
                collateralAsset {
                    address
                    symbol
                    decimals
                }
                state {
                    borrowAssets
                    supplyAssets
                    borrowAssetsUsd
                    supplyAssetsUsd
                    utilization
                    supplyApy
                    borrowApy
                }
            }
        }
    }
"""

# Add new GraphQL query
GET_VAULT = """
    query getVault($vaultId: String!) {
        vaultByAddress(address: $vaultId, chainId: 8453) {
            state {
                allTimeApy
                apy
                totalAssets
                totalAssetsUsd
                allocation {
                    market {
                        id
                        uniqueKey
                        irmAddress
                        oracleAddress
                    }
                    supplyAssets
                    supplyCap
                }
            }
            asset {
                id
                decimals
            }
        }
    }
"""

MORPHO_API_URL = "https://blue-api.morpho.org/graphql"
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base

# Load ABI
MORPHO_ABI = json.loads(
    (Path(__file__).parent.parent / "abi" / "morpho-blue.json").read_text()
)

class Asset(BaseModel):
    """Asset information"""
    address: str
    symbol: str
    decimals: int

class MarketState(BaseModel):
    """Market state information"""
    borrowAssets: int
    supplyAssets: int
    borrowAssetsUsd: float
    supplyAssetsUsd: float
    utilization: float
    supplyApy: float
    borrowApy: float

class Market(BaseModel):
    """Market information"""
    id: str
    lltv: float
    uniqueKey: str
    irmAddress: str
    oracleAddress: str
    loanAsset: Asset
    collateralAsset: Asset | None
    state: MarketState

class MarketResponse(BaseModel):
    """Response from market query"""
    items: List[Market]

class MarketAllocation(BaseModel):
    """Market allocation information"""
    market: Dict[str, str]  # Contains id and uniqueKey
    supplyAssets: int  # Changed from str to int
    supplyCap: int    # Changed from str to int

class VaultState(BaseModel):
    """Vault state information"""
    allTimeApy: float
    apy: float
    totalAssets: int  # Changed from str to int
    totalAssetsUsd: float
    allocation: List[MarketAllocation]

class VaultAsset(BaseModel):
    """Vault asset information"""
    id: str
    decimals: int

class VaultResponse(BaseModel):
    """Response from vault query"""
    state: VaultState
    asset: VaultAsset

@dataclass
class MarketInfo:
    """Information about a market that the vault is allocated to"""
    market_id: str  # uniqueKey
    loan_symbol: str
    collateral_symbol: str
    lltv: float
    
    @property
    def display_name(self) -> str:
        """Human readable market name with LLTV in percentage"""
        # Convert LLTV from 1e18 format to percentage
        lltv_percentage = (self.lltv / 1e18) * 100
        return f"{self.loan_symbol}-{self.collateral_symbol} ({lltv_percentage:.0f}%)"

async def get_morpho_markets() -> List[Market]:
    """Fetch all USDC markets from Morpho"""
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
                    "query": GET_MARKETS,
                    "variables": variables
                }
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if "errors" in data:
                    raise Exception(f"GraphQL errors: {data['errors']}")
                
                markets = MarketResponse(
                    items=[Market(**m) for m in data["data"]["markets"]["items"]]
                ).items
                
                return [m for m in markets if m.collateralAsset is not None]
                
        except Exception as e:
            logger.error(f"Error fetching Morpho markets: {str(e)}", exc_info=True)
            raise

@tool
async def fetch_all_morpho_markets() -> str:
    """
    Fetch all USDC markets from Morpho Blue protocol.
    
    Args:
        min_tvl: Optional minimum TVL to filter markets
        
    Returns:
        str: Formatted market information
    """
    try:
        markets = await get_morpho_markets()
        
        # Format response
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
    """
    Fetch the market status for a specific Morpho vault.
  
        
    Returns:
        str: Formatted analysis of markets
    """

    try:
        # Fetch vault data
        async with aiohttp.ClientSession() as session:
            variables = {"vaultId": VAULT_ADDRESS}
            async with session.post(
                MORPHO_API_URL,
                json={
                    "query": GET_VAULT,
                    "variables": variables
                }
            ) as response:
                response.raise_for_status()
                vault_data = await response.json()
                if "errors" in vault_data:
                    raise Exception(f"GraphQL errors: {vault_data['errors']}")
                
                vault = VaultResponse(**vault_data["data"]["vaultByAddress"])

        # Fetch all markets
        markets = await get_morpho_markets()
        
        # Create set of approved market IDs
        approved_market_ids = {
            alloc.market["id"] 
            for alloc in vault.state.allocation
        }
        
        # Split markets into approved and others
        approved_markets = []
        other_markets = []
        
        for market in markets:
            if market.id in approved_market_ids:
                approved_markets.append(market)
            else:
                other_markets.append(market)
        
        # Format response
        response = [
            f"Vault Analysis (${vault.state.totalAssetsUsd:,.2f} TVL)",
            f"Current APY: {vault.state.apy * 100:.2f}%",
            f"All-time APY: {vault.state.allTimeApy * 100:.2f}%\n"
        ]
        
        # Add approved markets section
        response.append("\n🟢 Approved Markets (Can reallocate):")
        for market in approved_markets:
            allocation = next(
                (a for a in vault.state.allocation if a.market["id"] == market.id),
                None
            )
            cap = allocation.supplyCap / (10 ** market.loanAsset.decimals) if allocation else 0
            current_supply = allocation.supplyAssets / (10 ** market.loanAsset.decimals) if allocation else 0
            
            response.append(
                f"\n- {market.collateralAsset.symbol}-{market.loanAsset.symbol}"
                f"\n  ID: {market.uniqueKey}"
                f"\n  TVL: ${market.state.supplyAssetsUsd:,.2f}"
                f"\n  Current Supply: {current_supply:,.2f} {market.loanAsset.symbol}"
                f"\n  Supply Cap: {cap:,.2f} {market.loanAsset.symbol}"
                f"\n  Utilization: {market.state.utilization * 100:.1f}%"
                f"\n  Supply APY: {market.state.supplyApy * 100:.2f}%"
                f"\n  Borrow APY: {market.state.borrowApy * 100:.2f}%"
                f"\n  Parameters:"
                f"\n    Loan: {market.loanAsset.address}"
                f"\n    Collateral: {market.collateralAsset.address}"
                f"\n    IRM: {market.irmAddress}"
                f"\n    Oracle: {market.oracleAddress}"
                f"\n    LLTV: {market.lltv}"
            )
            
        # Add other markets section
        response.append("\n\n🔵 Other Available Markets:")
        for market in other_markets:
            response.append(
                f"\n- {market.collateralAsset.symbol}-{market.loanAsset.symbol}"
                f"\n  TVL: ${market.state.supplyAssetsUsd:,.2f}"
                f"\n  Utilization: {market.state.utilization * 100:.1f}%"
                f"\n  Supply APY: {market.state.supplyApy * 100:.2f}%"
                f"\n  Borrow APY: {market.state.borrowApy * 100:.2f}%"
                f"\n  Parameters:"
                f"\n    USDC: {market.loanAsset.address}"
                f"\n    Collateral: {market.collateralAsset.address}"
                f"\n    IRM: {market.irmAddress}"
                f"\n    Oracle: {market.oracleAddress}"
                f"\n    LLTV: {market.lltv}"
            )
        
        return "\n".join(response)
        
    except Exception as e:
        logger.error(f"Error analyzing vault markets: {str(e)}", exc_info=True)
        return f"Error analyzing vault markets: {str(e)}"

async def get_vault_allocations() -> List[MarketInfo]:
    """Fetch all markets that the vault is allocated to"""
    async with aiohttp.ClientSession() as session:
        try:
            variables = {"vaultId": VAULT_ADDRESS}
            
            async with session.post(
                MORPHO_API_URL,
                json={
                    "query": GET_VAULT,
                    "variables": variables
                }
            ) as response:
                response.raise_for_status()
                vault_data = await response.json()
                if "errors" in vault_data:
                    raise Exception(f"GraphQL errors: {vault_data['errors']}")
                
                # Get all markets first for symbol lookup
                markets = await get_morpho_markets()
                markets_by_id = {m.id: m for m in markets}
                
                vault = VaultResponse(**vault_data["data"]["vaultByAddress"])
                
                # Build market info objects
                market_infos = []
                for allocation in vault.state.allocation:
                    market_id = allocation.market["uniqueKey"]
                    market = markets_by_id.get(allocation.market["id"])
                    
                    if market:
                        market_infos.append(MarketInfo(
                            market_id=market_id,
                            loan_symbol=market.loanAsset.symbol,
                            collateral_symbol=market.collateralAsset.symbol,
                            lltv=market.lltv
                        ))
                
                return market_infos
                
        except Exception as e:
            logger.error(f"Error fetching vault allocations: {str(e)}")
            raise

class MarketReader:
    def __init__(self, web3: Web3):
        self.web3 = web3
        self.morpho = self.web3.eth.contract(
            address=Web3.to_checksum_address("0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"),
            abi=MORPHO_ABI
        )
    
    async def get_market_data(self, market_id: str) -> dict:
        """Get market data from MorphoBlue contract"""
        try:
            # Convert market_id to proper format if needed
            if not market_id.startswith('0x'):
                market_id = f"0x{market_id}"
            
            # Call market() function
            market = self.morpho.functions.market(market_id).call()
            
            # Calculate liquidity
            supply_assets = int(market[0])  # totalSupplyAssets
            borrow_assets = int(market[2])  # totalBorrowAssets
            liquidity = supply_assets - borrow_assets
            
            return {
                'supply_assets': supply_assets,
                'borrow_assets': borrow_assets,
                'liquidity': liquidity
            }
        except Exception as e:
            print(f"Error reading market data: {e}")
            return None

