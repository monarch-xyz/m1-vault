# For direct contract interactions
from web3 import Web3
from typing import Dict
import json
from pathlib import Path
from .constants import MORPHO_BLUE_ADDRESS  # Update import

MORPHO_ABI = json.loads(
    (Path(__file__).parent.parent / "abi" / "morpho-blue.json").read_text()
)

class MarketReader:
    def __init__(self, web3: Web3):
        self.web3 = web3
        self.morpho = self.web3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),  # Use constant
            abi=MORPHO_ABI
        )
    
    async def get_market_data(self, market_id: str) -> dict:
        """Get market data directly from MorphoBlue contract"""
        try:
            if not market_id.startswith('0x'):
                market_id = f"0x{market_id}"
            
            market = self.morpho.functions.market(market_id).call()
            
            supply_assets = int(market[0])
            borrow_assets = int(market[2])
            liquidity = supply_assets - borrow_assets
            
            return {
                'supply_assets': supply_assets,
                'borrow_assets': borrow_assets,
                'liquidity': liquidity
            }
        except Exception as e:
            print(f"Error reading market data: {e}")
            return None 