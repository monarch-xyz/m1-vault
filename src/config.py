import os
from dotenv import load_dotenv

env = os.getenv('ENV', 'develop')
env_file = '.env.develop' if env == 'develop' else '.env'
load_dotenv(env_file)

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAIN_RPC_URL = os.getenv("RPC_URL")
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_TYPE = os.getenv("MODEL_TYPE", "anthropic")
