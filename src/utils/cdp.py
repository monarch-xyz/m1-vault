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

logger = logging.getLogger(__name__)

MORPHO_VAULT_ABI = [
    {
        "type": "function",
        "name": "isAllocator",
        "inputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "view"
    },
    {
        "type": "function",
        "name": "reallocate",
        "inputs": [
            {
                "internalType": "struct MarketAllocation[]",
                "name": "allocations",
                "type": "tuple[]",
                "components": [
                    {
                        "internalType": "struct MarketParams",
                        "name": "marketParams",
                        "type": "tuple",
                        "components": [
                            { "internalType": "address", "name": "loanToken", "type": "address" },
                            { "internalType": "address", "name": "collateralToken", "type": "address" },
                            { "internalType": "address", "name": "oracle", "type": "address" },
                            { "internalType": "address", "name": "irm", "type": "address" },
                            { "internalType": "uint256", "name": "lltv", "type": "uint256" }
                        ]
                    },
                    { "internalType": "uint256", "name": "assets", "type": "uint256" }
                ]
            }
        ],
        "outputs": [],
        "stateMutability": "nonpayable"
    }
]

IS_ALLOCATOR_PROMPT = """
This tool checks if an address is an allocator in the Morpho vault.
It takes:
- address: The address to check (e.g. 0x1234...)
"""

REALLOCATE_PROMPT = """
This tool reallocates assets across different markets in the Morpho vault.
It takes:
- vault_address: The address of the Morpho Vault
- allocations: New list of market allocations with their parameters and new asset amount. For the last market which is a "supply" (increase in asset), simplily put MAX_UINT256 to move remaining to this market

Example:
```
vault_address: 0x346aac1e83239db6a6cb760e95e13258ad3d1a6d
allocations:
    Allocation[0]
    - market_params:
        loan_token: 0x1234...
        collateral_token: 0x1234...
        oracle: 0x1234...
        irm: 0x1234...
        lltv: 1000000000000000000
    - assets: 0 (remove assets from this market)
    Allocation[1]
    - market_params:
        loan_token: 0x1234...
        collateral_token: 0x4444...
        oracle: 0x1234...
        irm: 0x1234...
        lltv: 1000000000000000000
    - assets: '0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff' (move all remaining assets to this market)
```


"""

class MorphoIsAllocatorInput(BaseModel):
    """Input schema for Morpho Vault isAllocator action."""
    
    address: str = Field(
        ...,
        description="The address to check if it's an allocator"
    )
    vault_address: str = Field(
        ...,
        description="The address of the Morpho Vault to check"
    )

class MarketParams(BaseModel):
    """Market parameters for Morpho markets."""
    loan_token: str = Field(..., description="Address of the loan token")
    collateral_token: str = Field(..., description="Address of the collateral token")
    oracle: str = Field(..., description="Address of the oracle")
    irm: str = Field(..., description="Address of the interest rate model")
    lltv: int = Field(..., description="Liquidation LTV (loan-to-value ratio)")

class MarketAllocation(BaseModel):
    """Market allocation with parameters and amount."""
    market_params: MarketParams = Field(..., description="Market parameters")
    assets: int = Field(..., description="Amount of assets to allocate")

class MorphoReallocateInput(BaseModel):
    """Input schema for Morpho Vault reallocate action."""
    vault_address: str = Field(..., description="The address of the Morpho Vault")
    allocations: list[MarketAllocation] = Field(..., description="List of market allocations")

def check_is_allocator(
    wallet: Wallet,
    vault_address: str,
    address: str,
) -> str:
    """Check if address is an allocator in Morpho vault.
    
    Args:
        wallet (Wallet): The wallet to execute the check from
        vault_address (str): The address of the Morpho Vault
        address (str): The address to check
        
    Returns:
        str: Message indicating if address is an allocator
    """
    try:
        is_allocator = SmartContract.read(
            network_id=wallet.network_id,
            contract_address=vault_address,
            method="isAllocator",
            abi=MORPHO_VAULT_ABI,
            args={"": address}
        )
        return f"The address {address} is{' ' if is_allocator else ' not '}an allocator"
    except Exception as e:
        return f"Error checking allocator status: {e!s}"

def reallocate(
    wallet: Wallet,
    vault_address: str,
    allocations: list[MarketAllocation],
) -> str:
    """Reallocate assets across different markets.
    
    Args:
        wallet (Wallet): The wallet to execute the transaction from
        vault_address (str): The address of the Morpho Vault
        allocations (list[MarketAllocation]): List of market allocations
        
    Returns:
        str: Transaction status message
    """
    try:
        # Convert the allocations to the format expected by SDK (tuple)
        formatted_allocations = [
            
            # tuple of loan_token, collateral_token, oracle, irm, lltv
            [
                [
                    alloc["market_params"]["loan_token"],
                    alloc["market_params"]["collateral_token"],
                    alloc["market_params"]["oracle"],
                    alloc["market_params"]["irm"],
                    alloc["market_params"]["lltv"],
                ],
                alloc["assets"]
            ] for alloc in allocations
        ]

        # convert to json
        
        tx = wallet.invoke_contract(
            contract_address=vault_address,
            method="reallocate",
            abi=MORPHO_VAULT_ABI,
            args={"allocations": formatted_allocations}
        )
        return f"Reallocation transaction submitted: {tx.hash}"
    except Exception as e:
        return f"Error during reallocation: {e!s}"

def get_reallocation_tool():
    cdp_wrapper = CdpAgentkitWrapper(
        cdp_api_key_name=os.getenv("CDP_API_KEY_NAME"),
        cdp_api_key_private_key=os.getenv("CDP_API_PRIVATE_KEY"),
        network_id=os.getenv("NETWORK_ID"),
        mnemonic_phrase=os.getenv("MNEMONIC_PHRASE"),
    )

    reallocate_tool = CdpTool(
        name="morpho_reallocate",
        description=REALLOCATE_PROMPT,
        cdp_agentkit_wrapper=cdp_wrapper,
        args_schema=MorphoReallocateInput,
        func=reallocate,
    )

    return reallocate_tool

def setup_cdp_toolkit():
    """Initialize CDP toolkit with credentials from environment."""
    try:
        cdp_wrapper = CdpAgentkitWrapper(
            cdp_api_key_name=os.getenv("CDP_API_KEY_NAME"),
            cdp_api_key_private_key=os.getenv("CDP_API_PRIVATE_KEY"),
            network_id=os.getenv("NETWORK_ID"),
            mnemonic_phrase=os.getenv("MNEMONIC_PHRASE"),
        )

        cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(cdp_wrapper)
        tools = cdp_toolkit.get_tools()

        # Add custom tools
        isAllocatorTool = CdpTool(
            name="morpho_is_allocator",
            description=IS_ALLOCATOR_PROMPT,
            cdp_agentkit_wrapper=cdp_wrapper,
            args_schema=MorphoIsAllocatorInput,
            func=check_is_allocator,
        )
        
        reallocateTool = CdpTool(
            name="morpho_reallocate",
            description=REALLOCATE_PROMPT,
            cdp_agentkit_wrapper=cdp_wrapper,
            args_schema=MorphoReallocateInput,
            func=reallocate,
        )
        
        tools.extend([isAllocatorTool, reallocateTool])

        logger.info("CDP toolkit initialized successfully.")
        return tools
    except ValueError as e:
        logger.error(f"Failed to initialize CDP toolkit: {str(e)}")
        return None