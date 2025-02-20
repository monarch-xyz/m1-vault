import os
from supabase import create_client, Client
from typing import Optional
from datetime import datetime, timedelta, timezone

class SupabaseClient:
    _instance: Optional[Client] = None

    @classmethod
    def init(cls):
        """Initialize Supabase client"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        
        cls._instance = create_client(supabase_url, supabase_key)
        return cls._instance

    @classmethod
    def get_client(cls) -> Client:
        """Get Supabase client instance"""
        if not cls._instance:
            cls._instance = cls.init()
        return cls._instance

    @classmethod
    async def store_message(cls, data: dict):
        """Store message in the user-messages table"""
        try:
            client = cls.get_client()
            result = client.table('user-messages').insert(data).execute()
            return result
        except Exception as e:
            print(f"Error storing message: {e}")
            raise

    @classmethod
    async def store_onchain_events(cls, data: dict):
        """Store message in the user-messages table"""
        try:
            client = cls.get_client()
            result = client.table('onchain-events').insert(data).execute()
            return result
        except Exception as e:
            print(f"Error storing message: {e}")
            raise

    @classmethod
    async def store_memories(cls, data: dict):
        """Store memories in the memories table"""
        try:
            print("Storing memories......")
            client = cls.get_client()
            result = client.table('memories').insert(data).execute()
            return result
        except Exception as e:
            print(f"Error storing memories: {e}")
            raise

    @classmethod
    async def get_filtered_market_events(cls, hours_ago: int = 1):
        """Get filtered events from the last N hours"""
        try:
            client = cls.get_client()
            
            # Calculate time range with explicit timezone format
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_ago)
            
            # Format timestamps to match exactly how they're stored
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
            
            response = client.table('onchain-events') \
                .select('*') \
                .gte('created_at', start_str) \
                .lte('created_at', end_str) \
                .execute()
            
            return response.data

        except Exception as e:
            print(f"Error fetching filtered events: {str(e)}")
            return None

    @classmethod
    async def store_market_snapshot(cls, data: dict):
        """Store market snapshot in the market-snapshots table"""
        try:
            client = cls.get_client()
            result = client.table('market-snapshots').insert(data).execute()
            return result
        except Exception as e:
            print(f"Error storing market snapshot: {e}")
            raise