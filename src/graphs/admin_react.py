from typing import TypedDict, Literal, Annotated, Sequence
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
from utils import get_reallocation_tool
import json
from utils.market import fetch_all_morpho_markets, fetch_vault_market_status, VAULT_ADDRESS
from utils.memory import add_long_term_memory, get_long_term_memory
from utils.reasoning import market_analysis
from utils.model_util import get_llm

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

tools = [
    # Disable temporary reallocation tool
    # get_reallocation_tool(),
    fetch_vault_market_status,
    fetch_all_morpho_markets,
    add_long_term_memory,
    get_long_term_memory,
    market_analysis
]

executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False)

# use a ReAct node to automatically choose tools and execute transactions
react_agent = create_react_agent(
    executor_llm,
    tools=tools,
    checkpointer=memory,
    state_modifier="""You are an assistant that govern morpho vault, who is in charge of balancing the supplied asset across different markets with in vault.
    You listen to the admin message and execute the command.

    The vault address is {}. 
    Once you receive the command, use coinbase CDP toolkit to execute on-chain transactions.
    You have access to the following tools:
    
    - fetch_all_morpho_markets
    - fetch_vault_market_status
    - morpho_reallocate
    - market_analysis: Use this tool to have deep and thorough reasoning about market, vaults, or others, make sure to provide data you gather from other tools

    - add_long_term_memory: Use it when the admin provide objective insights that would help analyze the market in the future. Do not store temporary data like util rate or market rate.
    - get_long_term_memory: Use it to find potential relevant insight from the long term memory.
    """.format(VAULT_ADDRESS),
)

