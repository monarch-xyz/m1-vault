from typing import TypedDict, Literal, Annotated, Sequence
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
from utils import get_user_shares_tool
import json
from utils.market_tools import create_market_tools
from utils.constants import VAULT_ADDRESS
from utils.memory import add_long_term_memory, get_long_term_memory
from utils.model_util import get_llm
from utils.reasoning import create_reasoning_tool

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

# Factory function to create the agent with access to the WebSocket manager
def create_user_agent(agent):
    # Get market tools with agent access for WebSocket broadcasting
    market_tools = create_market_tools(agent)
    
    # Get reasoning tool with agent access
    market_analysis = create_reasoning_tool(agent)
    
    tools = [
        get_user_shares_tool(),
        *market_tools,
        get_long_term_memory,
        market_analysis,
    ]

    executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=True)
    
    # Create the React agent with the tools
    react_agent = create_react_agent(
        executor_llm,
        tools=tools,
        checkpointer=memory,
        state_modifier="""Your name is M1 Agent, a manager of Morpho Vault, who give insights and analysis across different markets within the vault.
        You listen to the user message and friendly response to user, in easy and casual tone.

        You talk briefly, usually 2-3 sentences max, answer user question or handle the direct response to the user.  

        When you detect user deposits, you should greet them and welcome them to the vault.

        The vault address is {}. 
        You have access to the following tools:
        - fetch_all_morpho_markets
        - fetch_vault_market_status
        - morpho_get_shares
        - market_analysis: Use this tool to have deep and thorough reasoning about market, vaults, or others. make sure to provide data you gather from other tools
        """.format(VAULT_ADDRESS),
    )
    
    return react_agent
