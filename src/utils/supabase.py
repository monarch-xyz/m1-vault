import os
from supabase import create_client, Client
from typing import Optional

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
    async def store_thoughts(cls, data: dict):
        """Store thoughts in the thoughts table"""
        try:
            client = cls.get_client()
            result = client.table('thoughts').insert(data).execute()
            return result
        except Exception as e:
            print(f"Error storing thoughts: {e}")
            raise