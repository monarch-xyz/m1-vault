# For direct contract interactions
from web3 import Web3
from typing import Dict, List, Tuple
import json
from pathlib import Path
from .constants import MORPHO_BLUE_ADDRESS  # Update import
import logging

logger = logging.getLogger(__name__)

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
    
    async def get_vault_positions(self, vault_address: str, market_ids: List[str]) -> List[Dict]:
        """Get vault positions directly from MorphoBlue contract for multiple markets"""
        try:
            vault_address = Web3.to_checksum_address(vault_address)
            positions = []
            
            logger.info("Getting on-chain vault positions for %d markets", len(market_ids))
            for market_id in market_ids:
                if not market_id.startswith('0x'):
                    market_id = f"0x{market_id}"
                
                # Get position data
                position = self.morpho.functions.position(market_id, vault_address).call()
                supply_shares = int(position[0])
                
                # If the vault has supply shares, get the market data to convert shares to assets
                if supply_shares == 0:
                    continue

                market = self.morpho.functions.market(market_id).call()
                total_supply_shares = int(market[1])  # totalSupplyShares
                total_supply_assets = int(market[0])  # totalSupplyAssets
                
                # Convert shares to assets (if totalSupplyShares is 0, then assets is also 0)
                supply_assets = 0
                if total_supply_shares > 0:
                    supply_assets = (supply_shares * total_supply_assets) // total_supply_shares

                positions.append({
                    'market_id': market_id,
                    'supply_shares': supply_shares,
                    'supply_assets': supply_assets
                })
            
            return positions
        except Exception as e:
            print(f"Error reading vault positions: {e}")
            return [] 