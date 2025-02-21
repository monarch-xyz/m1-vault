from typing import TypedDict, Literal, Annotated, Sequence
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
from utils import get_reallocation_tool
import json
from utils.market_tools import fetch_vault_market_status, fetch_all_morpho_markets
from utils.memory import add_long_term_memory, get_long_term_memory
from utils.reasoning import market_analysis
from utils.model_util import get_llm
from utils.constants import VAULT_ADDRESS

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

tools = [
    get_reallocation_tool(),
    fetch_vault_market_status,
    fetch_all_morpho_markets,
    market_analysis
]

executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False)

# use a ReAct node to automatically choose tools and execute transactions
react_agent = create_react_agent(
    executor_llm,
    tools=tools,
    checkpointer=memory,
    state_modifier="""You are an DeFi lending risk manager who monitor the real time data of a morpho vault.

    You monitor all the real time data of markets, and make decisions whether there is massive risk in the vault.
    
    - morpho_reallocate: Use this tool to reallocate funds from risky market to safer markets if needed.

    """.format(VAULT_ADDRESS),
)

