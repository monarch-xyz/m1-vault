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
from utils.constants import VAULT_ADDRESS
from utils.market_api import MorphoAPIClient
import asyncio

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

Example: Reallocate 100 USDC from market A to market B and market C.
At the beginning, market A has 300 USDC, market B has 100 USDC, and market C has 100 USDC.
After reallocation, market A has 200 USDC, market B has 150 USDC, market C has 150 USDC.
Parameters:
```
vault_address: 0x346AAC1E83239dB6a6cb760e95E13258AD3d1A6d
from_markets: [
    {        
        loan_token: 0x1234...
        collateral_token: 0x1234...
        oracle: 0x1234...
        irm: 0x1234...
        lltv: 860000000000000000
    }
]
from_market_assets: [200000000]
to_markets: [
    {    
        loan_token: 0x1234...
        collateral_token: 0x4444...
        oracle: 0x1234...
        irm: 0x1234...
        lltv: 770000000000000000
    },
    {
        loan_token: 0x1234...
        collateral_token: 0x5555...
        oracle: 0x663B...
        irm: 0x4641...
        lltv: 860000000000000000
    }
]
to_market_assets: [150000000, 150000000]
```
"""

REALLOCATE_PROMPT_2 = """
This tool reallocate assets to a given allocation.

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
"""

class MarketParams(BaseModel):
    """Market parameters for Morpho markets."""
    loan_token: str = Field(..., description="Address of the loan token")
    collateral_token: str = Field(..., description="Address of the collateral token")
    oracle: str = Field(..., description="Address of the oracle")
    irm: str = Field(..., description="Address of the interest rate model")
    lltv: str = Field(..., description="Liquidation LTV (loan-to-value ratio) e.g. 770000000000000000 for 77%")

class MorphoReallocateInput(BaseModel):
    """Input schema for Morpho Vault reallocate action."""
    vault_address: str = Field(..., description="The address of the Morpho Vault")
    from_markets: list[MarketParams] = Field(..., description="The markets to move assets from")
    from_markets_assets: list[int] = Field(..., description="The exact amount of assets with decimal to retain in each market (in the same order as from_markets) e.g. [200210000] for 200.21 USDC")
    to_markets: list[MarketParams] = Field(..., description="The markets to move assets to")
    to_markets_assets: list[int] = Field(..., description="The exact amount of assets with decimal to allocate to each market (in the same order as to_markets) e.g. [150000000, 150250000] for 150 USDC, 150.25 USDC")

class MorphoReallocateInput2(BaseModel):
    """Input schema for Morpho Vault reallocate action."""
    market_ids: list[str] = Field(..., description="The IDs of the markets to reallocate assets. From market first, then to markets.")
    new_allocations: list[int] = Field(..., description="The exact amount of assets with decimal to allocate to each market (in the same order as market_ids) e.g. [200000000, 150000000, 150000000] for 200 USDC, 150 USDC, 150 USDC")

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


        # Encode reallocation call
        calldata = encode_reallocation(allocations)
        
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
        # try return e.message
        if hasattr(e, 'message'):
            return e.message
        else:
            return str(e)

def sync_wrapper(async_func):
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper

async def _get_market_params(market_ids: list[str]):
    """Async function to get market parameters."""
    return await MorphoAPIClient.get_market_params(market_ids)

get_market_params_sync = sync_wrapper(_get_market_params)

def reallocate_simple(
    wallet: Wallet,
    market_ids: list[str],
    new_allocations: list[str],
) -> str:
    """Reallocate assets across different markets."""
    try:
        # Format allocations
        allocations = []

        print("REALLOCATE FUNCTION TRIGGERED ------")
        
        # Use the sync wrapper to get market params
        market_params = get_market_params_sync(market_ids)
        print(market_params)
        
        for market_param, new_allocation in zip(market_params, new_allocations):
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
        
        # Encode reallocation call
        calldata = encode_reallocation(allocations)
        
        # Send via multicall
        invocation = wallet.invoke_contract(
            contract_address=VAULT_ADDRESS,
            method="multicall",
            abi=MORPHO_VAULT_ABI,
            args={"data": [calldata.hex()]}
        )

        print(invocation)
        message = f"Successfully reallocated USDC in Morpho Vault, with transaction hash: {invocation.transaction_hash}"

        await SupabaseClient.store_action("reallocate", message)
        return message
    except Exception as e:
        print("Error during reallocation", e)
        if hasattr(e, 'message'):
            return e.message
        else:
            return str(e)

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

        await SupabaseClient.store_action("get_shares", f"User {user_address} owns {shares_formatted:,.6f} vault shares")
        
        return f"User {user_address} owns {shares_formatted:,.6f} vault shares"
    except Exception as e:
        return f"Error checking user shares: {str(e)}"

def get_reallocation_tool():
    reallocate_tool = CdpTool(
        name="morpho_reallocate",
        description=REALLOCATE_PROMPT_2,
        cdp_agentkit_wrapper=cdp_wrapper,
        args_schema=MorphoReallocateInput2,
        func=reallocate_simple,
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