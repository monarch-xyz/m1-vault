from typing import TypedDict, Literal, Annotated, Sequence
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
from utils import get_reallocation_tool
import json
from utils.memory import add_long_term_memory, get_long_term_memory
from utils.reasoning import market_analysis
from utils.model_util import get_llm
from utils.constants import VAULT_ADDRESS

from langgraph.checkpoint.memory import MemorySaver

tools = []
# tools = [get_reallocation_tool()]

executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False)

# use a ReAct node to process input data and decide if any action is needed.
react_agent = create_react_agent(
    executor_llm,
    tools=tools,
    state_modifier="""
    You are an DeFi lending risk manager who monitor the real time data of a Morpho Vault, made up of multiple markets.

    You will be periodically given a summary of current vault and market data, and you need to figure out the best reallocation strategy. 
    You should reply like giving an update to the board members. (not a conversation)
    
    """.format(VAULT_ADDRESS),
)

