"""Morpho Vault action provider."""

import os
import json
from typing import Any, List
from web3 import Web3
from eth_abi import encode
from pathlib import Path
from coinbase_agentkit.action_providers.action_decorator import create_action
from coinbase_agentkit.action_providers.action_provider import ActionProvider
from coinbase_agentkit.network import Network
from coinbase_agentkit.wallet_providers import EvmWalletProvider
from pydantic import BaseModel, Field
from utils.market_api import MorphoAPIClient
from utils.market_onchain import MarketReader
from utils.market_api import MarketParams

VAULT_ADDRESS = "0x346AAC1E83239dB6a6cb760e95E13258AD3d1A6d"
MAX_UINT256 = 2**256 - 1

web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
market_reader = MarketReader(web3)

# import ABI from src/abi/morpho-vault.json
with open(Path(__file__).parent.parent / "abi" / "morpho-vault.json") as f:
    METAMORPHO_ABI = json.load(f)

class MorphoAssetMovement(BaseModel):
    """Input schema for Morpho Vault asset movement."""
    from_market_id: str = Field(..., description="The ID of the market to move assets from")
    to_market_id: str = Field(..., description="The ID of the market to move assets to")
    amount: int = Field(..., description="The amount of assets to move")

class MorphoReallocateInput(BaseModel):
    """Input schema for Morpho Vault reallocate action."""
    reallocations: list[MorphoAssetMovement] = Field(..., description="The list of asset movements to perform")

# class MorphoReallocateInput(BaseModel):
#     """Input schema for Morpho Vault reallocate action."""
#     market_ids: list[str] = Field(..., description="The IDs of the markets to reallocate assets. From market first, then to markets.")
#     new_allocations: list[int] = Field(..., description="The exact amount of assets with decimal to allocate to each market (in the same order as market_ids)")

class MorphoSharesInput(BaseModel):
    """Input schema for Morpho Vault shares action."""
    user_address: str = Field(..., description="The address of the user to get shares for")

# Define data structures for clarity and type safety
class Allocation(BaseModel):
    marketParams: MarketParams
    assets: int

def encode_reallocation(allocations: List[Allocation]):
    """Encode reallocate function call manually"""
    function_selector = Web3.to_bytes(hexstr="0x7299aa31") # 
    
    encoded_allocations = []
    for allocation in allocations:
        market_params = allocation.marketParams # Use attribute access
        encoded_allocation = [
            Web3.to_checksum_address(market_params.loan_token), # Use attribute access
            Web3.to_checksum_address(market_params.collateral_token), # Use attribute access
            Web3.to_checksum_address(market_params.oracle), # Use attribute access
            Web3.to_checksum_address(market_params.irm), # Use attribute access
            int(market_params.lltv), # Access attribute, ensure it's int
            int(allocation.assets) # Access attribute, ensure it's int
        ]
        encoded_allocations.append(encoded_allocation)

    encoded_params = encode(
        ['(address,address,address,address,uint256,uint256)[]'],
        [encoded_allocations]
    )

    return function_selector + encoded_params

class MorphoActionProvider(ActionProvider[EvmWalletProvider]):
    """Provides actions for interacting with Morpho Vaults."""

    def __init__(self):
        super().__init__("morpho-reallocator", [])

    @create_action(
        name="reallocate",
        description="""
This tool reallocate assets between morpho markets.

Example: 
To move 300 USDC in total, 100 USDC from market A to market B, and 200 USDC from market A to market C, use the following

reallocations: [
    {
        "from_market_id": "{market_a}",
        "to_market_id": "{market_b}",
        "amount": 100_000000
    }, 
    {
        "from_market_id": "{market_a}",
        "to_market_id": "{market_c}",
        "amount": 200_000000
    }
]
```
""",
        schema=MorphoReallocateInput,
    )
    def reallocate(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
        """Reallocate assets across different markets."""
        try:
            # Format allocations
            allocations_for_encoding: List[Allocation] = []

            # Get all market ids in the reallocations
            market_ids = []
            for reallocation in args["reallocations"]:
                if reallocation.from_market_id not in market_ids:
                    market_ids.append(reallocation.from_market_id)
                if reallocation.to_market_id not in market_ids:
                    market_ids.append(reallocation.to_market_id)

            # Get market parameters from API (mapped to market_ids)
            market_params = MorphoAPIClient.get_market_params_sync(market_ids)

            # Get all existing positions
            positions = MorphoAPIClient.get_vault_data_sync(VAULT_ADDRESS)

            market_delta: dict[str, int] = {}

            # Go through each reallocation, calculate the net change of assets
            for reallocation in args["reallocations"]:
                market_delta[reallocation.from_market_id] = market_delta.get(reallocation.from_market_id, 0) - reallocation.amount
                market_delta[reallocation.to_market_id] = market_delta.get(reallocation.to_market_id, 0) + reallocation.amount

            # sort market_delta, to have negative first (withdrawals first)
            market_delta = dict(sorted(market_delta.items(), key=lambda x: x[1]))

            # Build new allocations
            allocations_for_encoding = []

            # For each delta, get the market id, current liquidity, delta, and calculate the new allocation
            for market_id, delta in market_delta.items():
                # find market from the market_params
                market_param = market_params[market_id]

                if market_param is None:
                    print(f"Market {market_id} not found in market params --> Error")
                    continue

                # calculate the new allocation
                position = next((p for p in positions.state.allocation if p.market["uniqueKey"] == market_id), None)

                if position is None and delta < 0:
                    print(f"Market {market_id} not found in vault positions, but require withdrawal --> Error")
                    continue

                
                current_liquidity = position.supplyAssets if position else 0
                new_allocation = current_liquidity + delta

                allocations_for_encoding.append(Allocation(
                    marketParams=market_param,
                    assets=new_allocation
                ))

            # If the last operation processed was a supply, set its amount to MAX_UINT256
            if allocations_for_encoding and market_id:
                print(f"Setting assets to MAX_UINT256 for last withdrawal market: {market_id}")
                allocations_for_encoding[-1].assets = MAX_UINT256

            # Encode reallocation call
            calldata = encode_reallocation(allocations_for_encoding)
            
            # Send via multicall
            params = {
                "to": VAULT_ADDRESS,
                "data": '0x' + calldata.hex(),
            }

            tx_hash = wallet_provider.send_transaction(params)
            wallet_provider.wait_for_transaction_receipt(tx_hash)

            # return the tx hash if success
            return tx_hash

        except Exception as e:
            if hasattr(e, 'api_message'):
                return 'Reallocation failed: ' + e.api_message
            else:
                return 'Reallocation failed: ' + str(e)

    @create_action(
        name="get_shares",
        description="""
This tool gets the number of shares owned by a user in the Morpho vault.
It takes:
- user_address: The address of the user to get shares for

Example:
```
user_address: 0x1234...
```
""",
        schema=MorphoSharesInput,
    )
    def get_shares(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
        """Get the number of shares owned by a user in the Morpho vault."""
        try:
            # Create contract instance
            contract = Web3().eth.contract(address=VAULT_ADDRESS, abi=METAMORPHO_ABI)
            
            # Get shares balance
            shares = contract.functions.balanceOf(args["user_address"]).call()
            
            # Get decimals for proper formatting
            decimals = contract.functions.decimals().call()
            
            # Format shares with proper decimals
            shares_formatted = shares / (10 ** decimals)

            return f"User {args['user_address']} owns {shares_formatted:,.6f} vault shares"

        except Exception as e:
            return f"Error checking user shares: {str(e)}"

    def supports_network(self, network: Network) -> bool:
        """Check if the network is supported by this action provider."""
        return network.chain_id == "8453"


def morpho_action_provider() -> MorphoActionProvider:
    """Create a new Morpho action provider."""
    return MorphoActionProvider()
