from datetime import datetime, timezone
from collections import defaultdict
from handlers.base_handler import BaseHandler
from models.events import EventType
from utils.supabase import SupabaseClient
from utils.market import MarketReader
from web3 import Web3
import os

class PeriodicRiskHandler(BaseHandler):
    """Handler for periodic risk analysis"""
    
    def __init__(self, agent, logger):
        super().__init__(agent)
        self.logger = logger
        # Initialize Web3 and MarketReader
        self.web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.market_reader = MarketReader(self.web3)
        self.hours_ago = 1

    @property
    def subscribes_to(self):
        return [EventType.RISK_UPDATE]

    async def handle(self, event):
        """Handle periodic risk update events"""
        try:
            # Fetch last 1 hours of market events
            market_events = await SupabaseClient.get_filtered_market_events(hours_ago=self.hours_ago)
            
            # Calculate operations
            data = self.calculate_market_operations(market_events)
            summary = self.format_market_operations(data)
            print("[PeriodicRiskHandler] ", summary)
            
            # Update market snapshots
            await self.update_market_snapshots(data)
            
        except Exception as e:
            await self.logger.error("PeriodicRiskHandler", f"Error in risk update: {str(e)}")

    @staticmethod
    def calculate_market_operations(market_events):
        """Calculate operation stats from morpho market events"""
        if not market_events:
            return None
            
        # Initialize accumulators
        accumulated = {
            'borrow': 0,
            'supply': 0,
            'withdraw': 0,
            'repay': 0
        }
        
        # Initialize market breakdown
        markets = defaultdict(lambda: {
            'id': '',
            'borrow': 0,
            'supply': 0,
            'withdraw': 0,
            'repay': 0
        })
        
        # Process events
        for event in market_events:
            op_type = event['event']
            amount = float(event['amount']) if event['amount'] else 0
            market_id = event['market']
            
            # Update accumulated totals
            if op_type in accumulated:
                accumulated[op_type] += amount
            
            # Update market breakdown
            if market_id:
                markets[market_id]['id'] = market_id
                markets[market_id][op_type] += amount

        return {
            'accumulated': accumulated,
            'breakdown': list(markets.values())
        }

    @staticmethod
    def format_market_operations(data):
        """Format operations data into a text summary for LLM consumption"""
        if not data:
            return "No market operations detected in this period."
        
        summary_lines = ["Market Operations Summary:"]
        
        for market in data['breakdown']:
            operations = []
            for op_type in ['supply', 'withdraw', 'borrow', 'repay']:
                if market[op_type] > 0:
                    # Convert to USDC units only for display
                    amount_usdc = float(market[op_type]) / 1e6
                    operations.append(f"{op_type}: {amount_usdc:,.2f} USDC")
            
            if operations:
                summary_lines.append(f"\nMarket {market['id']}:")
                summary_lines.extend([f"- {op}" for op in operations])
        
        # Add accumulated totals
        summary_lines.append("\nAccumulated Totals:")
        for op_type, amount in data['accumulated'].items():
            if amount > 0:
                # Convert to USDC units only for display
                amount_usdc = float(amount) / 1e6
                summary_lines.append(f"Total {op_type}: {amount_usdc:,.2f} USDC")
        
        return "\n".join(summary_lines)

    async def update_market_snapshots(self, data):
        """Update market snapshots in Supabase"""
        if not data or not data['breakdown']:
            return
            
        now = datetime.now(timezone.utc)
        
        for market in data['breakdown']:
            market_id = market['id']
            
            # Get on-chain data
            market_data = await self.market_reader.get_market_data(market_id)
            if not market_data:
                continue
                
            # Prepare snapshot data with integer values
            snapshot = {
                'market': market_id,
                'interval': self.hours_ago * 3600,
                'liquidity': int(market_data['liquidity']),  # Convert to int
                'supply': int(market['supply']),
                'borrow': int(market['borrow']),
                'withdraw': int(market['withdraw']),
                'repay': int(market['repay'])
            }

            print('snapshot', snapshot)
            
            # Store in Supabase
            await SupabaseClient.store_market_snapshot(snapshot) 