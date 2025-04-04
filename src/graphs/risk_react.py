from typing import TypedDict, Literal, Annotated, Sequence
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
from utils.market_tools import create_market_tools
from utils.reasoning import create_reasoning_tool
from utils.model_util import get_llm
from utils.constants import VAULT_ADDRESS
from utils.cdp import cdp_tools
from langgraph.checkpoint.memory import MemorySaver

# Factory function to create the agent with access to the WebSocket manager
def create_risk_agent(agent):
    # Get market tools with agent access for WebSocket broadcasting
    market_tools = create_market_tools(agent)
    
    # Get reasoning tool with agent access
    market_analysis = create_reasoning_tool(agent)
    
    tools = [
        *cdp_tools,
        *market_tools,  # Use tools with broadcasting capability
        market_analysis
    ]
    
    # Use a smarter model for reasoning and generate updates
    executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False)
    
    # Create the React agent with the tools
    react_agent = create_react_agent(
        executor_llm,
        tools=tools,
        state_modifier="""
        You are a DeFi lending risk manager who monitors the real-time data of a Morpho Vault, composed of multiple markets.
        
        You will be periodically given a summary of current vault and underlying market data, and finally determine the best reallocation strategy (if any). 
        The reallocation strategy should consider the following:
        - Predicting interest rate change in the next hour
        - Balance risk and yield.
            - You Must not all-in one market. The biggest market cannot be more than 70% of the total assets
        
        - Act based on current constraints: 
            - [Liquidity Constraint]: If market A only has $1K liquidity, our current allocation is $5000, the max we can withdraw and move to another market is $1K. (resulting in new allocation of $4000 in Market A)
            - If allocation fails due to insufficient liquidity, it's caused by the above constraint. You need to adjust the "new allocation" array to put more asset in the original market.
        
        Most importnatly, you need to use the MorphoActionProvider_reallocate tool to execute the transaction after you determine the best strategy.

        Other useful tools:
        - market_analysis: Use it to have deeper insight on the market data.
        - MorphoActionProvider_reallocate: Use it to execute the reallocation transaction.
        - post_tweet: Use it to post a tweet.

        After you finish the report & the reallocation, you return a final response like giving an update to the community, be brief and to the point. (not a conversation)
        
        If you executed a reallocation, refine the final response into an insightful and engaging tweet and post it on Twitter.
        """.format(VAULT_ADDRESS),
    )
    
    return react_agent
