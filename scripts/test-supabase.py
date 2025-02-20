import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Add src to path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.append(src_path)

from utils.supabase import SupabaseClient
from handlers.periodic_risk_handler import PeriodicRiskHandler

async def main():
    load_dotenv()
    
    # Create and start schedule handler
    handler = PeriodicRiskHandler()
    
    handler.handle(None)

if __name__ == "__main__":
    asyncio.run(main())