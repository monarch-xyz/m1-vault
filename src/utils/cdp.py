"""CDP toolkit integration module."""
import os
import logging
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
]

IS_ALLOCATOR_PROMPT = """
This tool checks if an address is an allocator in the Morpho vault.
It takes:
- address: The address to check (e.g. 0x1234...)
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
        tools.append(isAllocatorTool)

        logger.info("CDP toolkit initialized successfully.")
        return tools
    except ValueError as e:
        logger.error(f"Failed to initialize CDP toolkit: {str(e)}")
        return None