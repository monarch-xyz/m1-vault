import os
from supabase import create_client, Client
from typing import Optional, Dict
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
    async def _store_data(cls, table: str, data: Dict, error_context: str):
        """Base method to store data in any table"""
        try:
            client = cls.get_client()
            result = client.table(table).insert(data).execute()
            return result
        except Exception as e:
            print(f"Error storing {error_context}: {e}")
            raise

    @classmethod
    async def _store_memory_table(cls, memory_type: str, sub_type: str, text: str, activity_id: str):
        """Base method to store data in the memories table, most information is stored here"""
        data = {
            "type": memory_type,
            "sub_type": sub_type,
            "text": text,
            "activity_id": activity_id
        }
        return await cls._store_data('memories', data, f"memory ({memory_type})")

    @classmethod
    async def store_message(cls, data: dict):
        """Store message in the user-messages table"""
        return await cls._store_data('user-messages', data, "message")

    @classmethod
    async def store_onchain_events(cls, data: dict):
        """Store onchain events"""
        return await cls._store_data('onchain-events', data, "onchain event")

    @classmethod
    async def store_market_snapshot(cls, data: dict):
        """Store market snapshot"""
        return await cls._store_data('market-snapshots', data, "market snapshot")

    @classmethod
    async def store_thought(cls, sub_type: str, text: str, activity_id: str):
        """Store thought in memories"""
        return await cls._store_memory_table("think", sub_type, text, activity_id)

    @classmethod
    async def store_report(cls, sub_type: str, text: str, activity_id: str):
        """Store report in memories"""
        return await cls._store_memory_table("report", sub_type, text, activity_id)

    @classmethod
    async def store_activity(cls, activity_id: str, full_history: list, trigger: str):
        """Store activity with full message history"""
        # Convert messages to serializable format
        serializable_history = []
        for message in full_history:
            serializable_history.append({
                "type": message.__class__.__name__,
                "content": message.content,
                "additional_kwargs": message.additional_kwargs
            })
            
        data = {
            "id": activity_id,
            "full_history": serializable_history,
            "trigger": trigger
        }
        return await cls._store_data('activities', data, "activity")

    @classmethod
    async def get_filtered_market_events(cls, hours_ago: int = 1):
        """Get filtered events from the last N hours"""
        try:
            client = cls.get_client()
            
            # Calculate time range with explicit timezone
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