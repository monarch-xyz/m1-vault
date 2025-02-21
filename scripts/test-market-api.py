import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Add src to path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.append(src_path)

from utils.market_api import MorphoAPIClient

async def main():
    load_dotenv()
    
    # Initialize MorphoAPIClient
    client = MorphoAPIClient()
    
    # Get all markets
    markets = await client.get_market_apys("0x13c42741a359ac4a8aa8287d2be109dcf28344484f91185f9a79bd5a805a55ae")
    print(markets)

if __name__ == "__main__":
    asyncio.run(main())