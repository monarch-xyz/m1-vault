from datetime import datetime
from collections import defaultdict
from handlers.base_handler import BaseHandler
from models.events import EventType
from utils.supabase import SupabaseClient

class PeriodicRiskHandler(BaseHandler):
    """Handler for periodic risk analysis"""
    
    def __init__(self, agent, logger):
        super().__init__(agent)
        self.logger = logger

    @property
    def subscribes_to(self):
        return [EventType.RISK_UPDATE]

    async def handle(self, event):
        """Handle periodic risk update events"""
        try:
            # Fetch last 1 hours of market events
            market_events = await SupabaseClient.get_filtered_market_events(hours_ago=1)
            
            # Calculate and format operations
            data = self.calculate_market_operations(market_events)
            summary = self.format_market_operations(data)
            
            # Log the summary
            print("[PeriodicRiskHandler] ", summary)
            
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
            amount = float(event['amount']) / 1e6 if event['amount'] else 0
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
                    operations.append(f"{op_type}: {market[op_type]:,.2f} USDC")
            
            if operations:
                summary_lines.append(f"\nMarket {market['id']}:")
                summary_lines.extend([f"- {op}" for op in operations])
        
        # Add accumulated totals
        summary_lines.append("\nAccumulated Totals:")
        for op_type, amount in data['accumulated'].items():
            if amount > 0:
                summary_lines.append(f"Total {op_type}: {amount:,.2f} USDC")
        
        return "\n".join(summary_lines) 