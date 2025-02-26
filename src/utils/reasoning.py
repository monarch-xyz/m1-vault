from langchain_core.tools import tool
from config import Config
from langchain_core.messages import HumanMessage, SystemMessage
from utils.supabase import SupabaseClient

from langgraph.prebuilt import create_react_agent
from .model_util import get_llm

import logging

# Get the standard Python logger
logger = logging.getLogger(__name__)

# use smarter model for reasoning
# for cost saving, we use the interpreter model
llm = get_llm(Config.MODEL_TYPE, is_interpreter=True)

prompt = """You are a DeFi expert in lending protocols.
Your job is to reason about the prompt and the data, and provide a detailed analysis.

For example: 
- When the interest rate of a market is high, meaning more borrowers, you consider the risk of low liquidity to withdraw, compare to our liquidity in the market, and access if it's worth the risk.

- When the interest rate of a market is low, you should check if it's caused by low utilization rate, and consider moving asset elsewhere to get higher APY.

- When a new perpective is provided, you should consider that with the current vault status

For knowledge:
- Markets have an optimal utilization rate of 90%, which is consider "balanced"

"""

@tool
async def market_analysis(reasoning_prompt: str, market_or_vault_data: str):
    """
    Giving the data and current stats, conduct a thorough reasoing about the prompt related to market analysis.
    Make sure to use this tool with other tools to gather data.

    For example:
    - Given the 35% rate of USDC-ezETH market, with low liquidity and high utilization rate (99%), is it a good idea to reallocate the asset to the market?

    Args:
        reasoning_prompt: The prompt to reason about
        market_or_vault_data: The data you gather from other tools
    """

    final_message = f"""
    {reasoning_prompt}

    Data:
    {market_or_vault_data}
    """
    
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=final_message)
    ])

    reasoning = response.content

    await SupabaseClient.store_thought("analysis", reasoning)

    return reasoning
