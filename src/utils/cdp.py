"""CDP toolkit integration module."""
import os
import logging
import json
from typing import Optional, Tuple, Callable
from cdp import Wallet
from cdp.smart_contract import SmartContract
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper
from cdp_langchain.tools import CdpTool
from pydantic import BaseModel, Field
from pathlib import Path
from web3 import Web3
from config import Config
from decimal import Decimal
from eth_abi import encode

MORPHO_VAULT_ABI_PATH = Path(__file__).parent.parent / "abi" / "morpho-vault.json"
with open(MORPHO_VAULT_ABI_PATH) as f:
    MORPHO_VAULT_ABI = json.load(f)

cdp_wrapper = CdpAgentkitWrapper(
    cdp_api_key_name=os.getenv("CDP_API_KEY_NAME"),
    cdp_api_key_private_key=os.getenv("CDP_API_PRIVATE_KEY"),
    network_id=os.getenv("NETWORK_ID"),
    mnemonic_phrase=os.getenv("MNEMONIC_PHRASE"),
)

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

REALLOCATE_PROMPT = """
This tool reallocates assets across different markets in the Morpho vault.
It takes:
- vault_address: The address of the Morpho Vault
- from_markets: The markets to move assets from
- from_markets_assets: The exact amount of assets with decimal to move from each market (in the same order as from_markets)
- to_markets: The markets to move assets to
- to_markets_assets: The exact amount of assets with decimal to move to each market (in the same order as to_markets)

Example:
```
vault_address: 0x346AAC1E83239dB6a6cb760e95E13258AD3d1A6d
from_market:
    loan_token: 0x1234...
    collateral_token: 0x1234...
    oracle: 0x1234...
    irm: 0x1234...
    lltv: 860000000000000000 (86%)
from_market_assets: [100000000, 200000000] (100 USDC, 200 USDC)
to_market:
    loan_token: 0x1234...
    collateral_token: 0x4444...
    oracle: 0x1234...
    irm: 0x1234...
    lltv: 770000000000000000 (77%)
to_market_assets: [100000000, 200000000] (100 USDC, 200 USDC)
```
"""

class MarketParams(BaseModel):
    """Market parameters for Morpho markets."""
    loan_token: str = Field(..., description="Address of the loan token")
    collateral_token: str = Field(..., description="Address of the collateral token")
    oracle: str = Field(..., description="Address of the oracle")
    irm: str = Field(..., description="Address of the interest rate model")
    lltv: str = Field(..., description="Liquidation LTV (loan-to-value ratio)")

class MorphoReallocateInput(BaseModel):
    """Input schema for Morpho Vault reallocate action."""
    vault_address: str = Field(..., description="The address of the Morpho Vault")
    from_markets: list[MarketParams] = Field(..., description="The markets to move assets from")
    from_markets_assets: list[int] = Field(..., description="The exact amount of assets with decimal to move from each market")
    to_markets: list[MarketParams] = Field(..., description="The markets to move assets to")
    to_markets_assets: list[int] = Field(..., description="The exact amount of assets with decimal to move to each market")

class MorphoSharesInput(BaseModel):
    """Input schema for Morpho Vault shares action."""
    vault_address: str = Field(..., description="The address of the Morpho Vault")
    user_address: str = Field(..., description="The address of the user to get shares for")

def reallocate(
    wallet: Wallet,
    vault_address: str,
    from_markets: list[MarketParams],
    from_markets_assets: list[int],
    to_markets: list[MarketParams],
    to_markets_assets: list[int],
) -> str:
    """Reallocate assets across different markets."""
    try:
        # Format allocations
        allocations = []
        
        for from_market, from_assets in zip(from_markets, from_markets_assets):
            allocations.append({
                'marketParams': {
                    'loanToken': from_market["loan_token"],
                    'collateralToken': from_market["collateral_token"],
                    'oracle': from_market["oracle"],
                    'irm': from_market["irm"],
                    'lltv': from_market["lltv"],
                },
                'assets': from_assets
            })
        
        for to_market, to_assets in zip(to_markets, to_markets_assets):
            allocations.append({
                'marketParams': {
                    'loanToken': to_market["loan_token"],
                    'collateralToken': to_market["collateral_token"],
                    'oracle': to_market["oracle"],
                    'irm': to_market["irm"],
                    'lltv': to_market["lltv"],
                },
                'assets': 2**256 - 1 if to_market == to_markets[-1] else to_assets
            })

        print("allocations", allocations)

        # Encode reallocation call
        calldata = encode_reallocation(allocations)

        print("calldata", calldata.hex())
        
        # Send via multicall
        invocation = wallet.invoke_contract(
            contract_address=vault_address,
            method="multicall",
            abi=MORPHO_VAULT_ABI,
            args={"data": [calldata.hex()]}
        )
        
        return f"Successfully reallocated USDC in Morpho Vault, with transaction hash: {invocation.transaction_hash} and transaction link: {invocation.transaction_link}"
    except Exception as e:
        print("Error during reallocation", e)
        return "Error during reallocation. Don't retry"

SHARES_PROMPT = """
This tool gets the number of shares owned by a user in the Morpho vault.
It takes:
- vault_address: The address of the Morpho Vault
- user_address: The address of the user to get shares for

Example:
```
vault_address: 0x346AAC1E83239dB6a6cb760e95E13258AD3d1A6d
user_address: 0x1234...
```
"""

def get_user_shares(
    wallet: Wallet,
    vault_address: str,
    user_address: str,
) -> str:
    """Get the number of shares owned by a user in the Morpho vault."""
    try:
        # Read balanceOf from the vault contract
        shares = SmartContract.read(
            network_id=wallet.network_id,
            contract_address=vault_address,
            method="balanceOf",
            abi=MORPHO_VAULT_ABI,
            args={"account": user_address}
        )
        
        # Get decimals for proper formatting
        decimals = SmartContract.read(
            network_id=wallet.network_id,
            contract_address=vault_address,
            method="decimals",
            abi=MORPHO_VAULT_ABI,
            args={}
        )
        
        # Format shares with proper decimals
        shares_formatted = shares / (10 ** decimals)
        
        return f"User {user_address} owns {shares_formatted:,.6f} vault shares"
    except Exception as e:
        return f"Error checking user shares: {str(e)}"

def get_reallocation_tool():
    reallocate_tool = CdpTool(
        name="morpho_reallocate",
        description=REALLOCATE_PROMPT,
        cdp_agentkit_wrapper=cdp_wrapper,
        args_schema=MorphoReallocateInput,
        func=reallocate,
    )

    return reallocate_tool

def get_user_shares_tool():
    return CdpTool(
        name="morpho_get_shares",
        description=SHARES_PROMPT,
        cdp_agentkit_wrapper=cdp_wrapper,
        args_schema=MorphoSharesInput,
        func=get_user_shares,
    )
    
def setup_cdp_toolkit():
    """Initialize CDP toolkit with credentials from environment."""
    try:
        cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(cdp_wrapper)
        tools = cdp_toolkit.get_tools()
        
        reallocateTool = CdpTool(
            name="morpho_reallocate",
            description=REALLOCATE_PROMPT,
            cdp_agentkit_wrapper=cdp_wrapper,
            args_schema=MorphoReallocateInput,
            func=reallocate,
        )
        
        sharesTool = CdpTool(
            name="morpho_get_shares",
            description=SHARES_PROMPT,
            cdp_agentkit_wrapper=cdp_wrapper,
            args_schema=MorphoSharesInput,
            func=get_user_shares,
        )
        
        tools.extend([reallocateTool, sharesTool])

        return tools
    except ValueError as e:
        print(f"Failed to initialize CDP toolkit: {str(e)}")
        return None