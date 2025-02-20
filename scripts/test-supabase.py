import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Add src to path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.append(src_path)

from utils.supabase import SupabaseClient

async def main():
    load_dotenv()
    
    # Initialize Supabase
    SupabaseClient.init()
    
    # Get market events from last hour
    events = await SupabaseClient.get_filtered_market_events(hours_ago=1)
    
    if not events:
        print("No events found")
        return
        
    print(f"\nFound {len(events)} events:")
    for event in events:
        print(f"\nTimestamp: {event['created_at']}")
        print(f"Market: {event['market']}")
        print(f"Type: {event['event']}")
        print(f"Amount: {float(event['amount'])/1e6:,.2f} USDC")
        print(f"Tx Hash: {event['data'].get('tx_hash', 'N/A')}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())