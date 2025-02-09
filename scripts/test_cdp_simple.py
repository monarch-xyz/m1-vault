import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_abi import encode
import json

# Add src to path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.append(src_path)

from utils.cdp_simple import CDPClient

# Load environment variables
load_dotenv()

# Initialize Web3
w3 = Web3()

# Contract addresses
VAULT_ADDRESS = "0x346AAC1E83239dB6a6cb760e95E13258AD3d1A6d"
MORPHO_BLUE_ADDRESS = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"

# Load ABI from src/abi
MORPHO_VAULT_ABI_PATH = Path(__file__).parent.parent / "src" / "abi" / "morpho-vault.json"
with open(MORPHO_VAULT_ABI_PATH) as f:
    MORPHO_VAULT_ABI = json.load(f)

# Market data
MARKET_1 = {
    "loan_token": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
    "collateral_token": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",  # cbETH
    "oracle": "0x663BECd10daE6C4A3Dcd89F1d76c1174199639B9",
    "irm": "0x46415998764C29aB2a25CbeA6254146D50D22687",
    "lltv": "860000000000000000"
}

MARKET_2 = {
    "loan_token": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
    "collateral_token": "0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A",  # rETH
    "oracle": "0x9DBcd79e1f47D95DE6F211bFB610f082Fc584406",
    "irm": "0x46415998764C29aB2a25CbeA6254146D50D22687",
    "lltv": "770000000000000000"
}

def encode_reallocation(allocations):
    """Encode reallocate function call manually"""
    # Function selector for reallocate((address,address,address,address,uint256,uint256)[])
    function_selector = Web3.to_bytes(hexstr="0x7299aa31")
    
    # Prepare the allocation data
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

    # Encode the parameters
    encoded_params = encode(
        ['(address,address,address,address,uint256,uint256)[]'],
        [encoded_allocations]
    )

    # Combine function selector with encoded parameters
    return function_selector + encoded_params

def main():
    # Initialize CDP client
    client = CDPClient()
    
    # Format allocations for encoding
    allocations = [
        # From market - withdraw everything
        {
            'marketParams': {
                'loanToken': MARKET_1["loan_token"],
                'collateralToken': MARKET_1["collateral_token"],
                'oracle': MARKET_1["oracle"],
                'irm': MARKET_1["irm"],
                'lltv': MARKET_1["lltv"],
            },
            'assets': 0
        },
        # To market - deposit everything
        {
            'marketParams': {
                'loanToken': MARKET_2["loan_token"],
                'collateralToken': MARKET_2["collateral_token"],
                'oracle': MARKET_2["oracle"],
                'irm': MARKET_2["irm"],
                'lltv': MARKET_2["lltv"],
            },
            'assets': 2**256 - 1  # MAX_UINT256
        }
    ]

    try:
        # Encode the reallocation call
        calldata = encode_reallocation(allocations)
        print("\nEncoded calldata:")
        print(calldata.hex())
        
        # Send transaction
        print("\nSending transaction...")
        tx_hash = client.send_transaction(
            contract_address=VAULT_ADDRESS,
            abi=MORPHO_VAULT_ABI,
            method="multicall",
            args={
              "data": [calldata.hex()]
            }
        )
        
        print(f"\nTransaction submitted successfully!")
        print(f"Transaction hash: {tx_hash}")
        
    except Exception as e:
        print(f"\nError sending transaction: {str(e)}")
        print(f"Full error: {repr(e)}")

if __name__ == "__main__":
    main() 