from typing import TypedDict, Literal, Annotated, Sequence
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
import json
from utils.market_tools import create_market_tools
from utils.memory import add_long_term_memory, get_long_term_memory
from utils.reasoning import create_reasoning_tool
from utils.model_util import get_llm
from utils.constants import VAULT_ADDRESS
from utils.cdp import cdp_tools
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

# Factory function to create the agent with access to the WebSocket manager
def create_admin_agent(agent):
    # Get market tools with agent access for WebSocket broadcasting
    market_tools = create_market_tools(agent)
    
    # Get reasoning tool with agent access
    market_analysis = create_reasoning_tool(agent)
    
    tools = [
        # Disable temporary reallocation tool
        *market_tools,  # Use tools with broadcasting capability
        *cdp_tools,
        add_long_term_memory,
        get_long_term_memory,
        market_analysis
    ]
    
    executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=True)
    
    # Create the React agent with the tools
    react_agent = create_react_agent(
        executor_llm,
        tools=tools,
        checkpointer=memory,
        state_modifier="""You are an assistant that govern morpho vault, who is in charge of balancing the supplied asset across different markets with in vault.
        You listen to the admin message and execute the command.

        The vault address is {}. 
        Once you receive the command, use coinbase CDP toolkit to execute on-chain transactions.
        You have access to the following tools:
        
        - fetch_vault_market_status
        - morpho_reallocate
        - market_analysis: Use this tool to have deep and thorough reasoning about market, vaults, or others, make sure to provide data you gather from other tools

        - add_long_term_memory: Use it when the admin provide objective insights that would help analyze the market in the future. Do not store temporary data like util rate or market rate.
        - get_long_term_memory: Use it to find potential relevant insight from the long term memory.
        """.format(VAULT_ADDRESS),
    )
    
    return react_agent
