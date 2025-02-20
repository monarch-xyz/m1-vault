import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

# Add src to path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.append(src_path)

from utils.supabase import SupabaseClient

# Initialize Supabase
SupabaseClient.init()
client = SupabaseClient.get_client()

async def get_market_operations(hours_ago: int = 1):
    """Get operation stats from the last N hours"""
    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_ago)
        
        # Fetch events
        response = client.table('onchain-events') \
            .select('*') \
            .gte('created_at', start_time.isoformat()) \
            .lte('created_at', end_time.isoformat()) \
            .execute()

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
        for event in response.data:
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

    except Exception as e:
        print(f"Error getting market operations: {e}")
        return None

def format_operations(data):
    """Format operations data for display"""
    if not data:
        return
    
    print("\n=== Accumulated Operations ===")
    total = 0
    for op_type, amount in data['accumulated'].items():
        total += amount
        print(f"{op_type.upper()}: {amount:,.2f} USDC")
    print(f"\nTotal Volume: {total:,.2f} USDC")
    
    print("\n=== Market Breakdown ===")
    for market in data['breakdown']:
        print(f"\nMarket: {market['id']}")
        market_total = sum(v for k, v in market.items() if k != 'id')
        print(f"Total Volume: {market_total:,.2f} USDC")
        for op_type in ['supply', 'withdraw', 'borrow', 'repay']:
            if market[op_type] > 0:
                print(f"- {op_type}: {market[op_type]:,.2f} USDC")

async def main():
    load_dotenv()
    
    # Get data
    data = await get_market_operations(hours_ago=30)
    
    # Format and display
    format_operations(data)

if __name__ == "__main__":
    asyncio.run(main())