# For Supabase database operations
from collections import defaultdict
from typing import Dict

from .supabase import SupabaseClient

async def get_market_operations(hours_ago: int = 1) -> Dict:
    """Get market operations from Supabase DB"""
    market_events = await SupabaseClient.get_filtered_market_events(hours_ago=hours_ago)
    if not market_events:
        return None
        
    markets = defaultdict(lambda: {
        'id': '',
        'borrow': 0,
        'supply': 0,
        'withdraw': 0,
        'repay': 0
    })
    
    for event in market_events:
        op_type = event['event']
        amount = float(event['amount']) if event['amount'] else 0
        market_id = event['market']

        if not op_type or not amount or not market_id:
            continue
        
        markets[market_id]['id'] = market_id
        markets[market_id][op_type] += amount

    return list(markets.values()) 