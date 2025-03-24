"""Morpho Vault action provider."""

from decimal import Decimal
from typing import Any
from web3 import Web3
from eth_abi import encode
from pathlib import Path
import json
from coinbase_agentkit.action_providers.action_decorator import create_action
from coinbase_agentkit.action_providers.action_provider import ActionProvider
from coinbase_agentkit.network import Network
from coinbase_agentkit.wallet_providers import EvmWalletProvider
from pydantic import BaseModel, Field
from utils.market_api import MorphoAPIClient
SUPPORTED_NETWORKS = ["base-mainnet", "base-sepolia"]
VAULT_ADDRESS = "0x346AAC1E83239dB6a6cb760e95E13258AD3d1A6d"

# import ABI from src/abi/morpho-vault.json
with open(Path(__file__).parent.parent / "abi" / "morpho-vault.json") as f:
    METAMORPHO_ABI = json.load(f)

class MorphoReallocateInput(BaseModel):
    """Input schema for Morpho Vault reallocate action."""
    market_ids: list[str] = Field(..., description="The IDs of the markets to reallocate assets. From market first, then to markets.")
    new_allocations: list[int] = Field(..., description="The exact amount of assets with decimal to allocate to each market (in the same order as market_ids)")

class MorphoSharesInput(BaseModel):
    """Input schema for Morpho Vault shares action."""
    user_address: str = Field(..., description="The address of the user to get shares for")

def encode_reallocation(allocations):
    """Encode reallocate function call manually"""
    function_selector = Web3.to_bytes(hexstr="0x7299aa31")
    
    encoded_allocations = []
    for allocation in allocations:
        market_params = allocation['marketParams']
        encoded_allocation = [
            Web3.to_checksum_address(market_params['loanToken']),
            Web3.to_checksum_address(market_params['collateralToken']),
            Web3.to_checksum_address(market_params['oracle']),
            Web3.to_checksum_address(market_params['irm']),
            int(market_params['lltv']),
            int(allocation['assets'])
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
This tool reallocate assets to a given allocation for a morpho vault.

Example: 
We want to move 100 USDC from market A to market B and market C, making the final allocation 200 USDC in market A, 150 USDC in market B, and 150 USDC in market C.

Parameters:
```
market_ids: [
    "a4e2843486610e6851f4e0a8fcdee819958598c71c7e99b0315904ccf162ddc3", ("market_a") (from)
    "8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda", ("market_b") (to)
    "13c42741a359ac4a8aa8287d2be109dcf28344484f91185f9a79bd5a805a55ae", ("market_c") (to)
]
new_allocations: [200000000, 150000000, 150000000]
```
""",
        schema=MorphoReallocateInput,
    )
    def reallocate(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
        """Reallocate assets across different markets."""
        try:
            # Format allocations
            allocations = []

            # Get market parameters from API
            market_params = MorphoAPIClient.get_market_params_sync(args["market_ids"])

            for market_param, new_allocation in zip(market_params, args["new_allocations"]):
                allocations.append({
                    'marketParams': {
                        'loanToken': market_param.loan_token,
                        'collateralToken': market_param.collateral_token,
                        'oracle': market_param.oracle,
                        'irm': market_param.irm,
                        'lltv': market_param.lltv,
                    },
                    'assets': 2**256 - 1 if market_param == market_params[-1] else new_allocation
                })

            # print allocations nicely: print the new allocations
            print("New allocations:")
            for market_id, allocation in zip(args["market_ids"], allocations):
                print(f"Market: {market_id}, Assets: {allocation['assets']}")

            # Encode reallocation call
            calldata = encode_reallocation(allocations)
            
            # Send via multicall
            params = {
                "to": VAULT_ADDRESS,
                "data": '0x' + calldata.hex(),
            }

            tx_hash = wallet_provider.send_transaction(params)
            wallet_provider.wait_for_transaction_receipt(tx_hash)

            return f"Successfully reallocated USDC in Morpho Vault with transaction hash: {tx_hash}"

        except Exception as e:
            if hasattr(e, 'api_message'):
                return e.api_message
            else:
                return str(e)

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
        return network.protocol_family == "evm" and network.network_id in SUPPORTED_NETWORKS


def morpho_action_provider() -> MorphoActionProvider:
    """Create a new Morpho action provider."""
    return MorphoActionProvider()
