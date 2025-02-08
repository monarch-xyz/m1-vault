from typing import TypedDict, Literal, Annotated, Sequence

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
from utils import get_reallocation_tool
import json
from utils.market import fetch_all_morpho_markets, fetch_vault_market_status, VAULT_ADDRESS

tools = [
    get_reallocation_tool(),
    fetch_vault_market_status,
    fetch_all_morpho_markets
]

# Initialize the vector store
# Todo: use different vector store for different types of knowledges
morpho_knowledge_store = Chroma(
    collection_name="morpho_knowledge",
    embedding_function=OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY),
    persist_directory="data/morpho_knowledge",
)

# Define model options
ModelType = Literal["anthropic", "openai"]

# Get LLM instance based on type and purpose
def get_llm(model_type: ModelType, is_interpreter: bool = False):
    """Get LLM instance based on type and purpose"""
    if (model_type == "anthropic"):
        model = "claude-3-5-haiku-20241022" if is_interpreter else "claude-3-5-sonnet-20241022"
        return ChatAnthropic(
            model=model,
            api_key=Config.ANTHROPIC_API_KEY
        )
    else:
        model = "gpt-4o-mini" if is_interpreter else "gpt-4o-2024-11-20"
        return ChatOpenAI(
            model=model,
            api_key=Config.OPENAI_API_KEY
        )

executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False)

# use a ReAct node to automatically choose toolsl to execute transactions
react_agent = create_react_agent(
    executor_llm,
    tools=tools,
    state_modifier="""You are an Morpho Vault, who balance the supplied asset across different markets with in vault.
    You listen to the admin message and execute the command.

    The vault address is {}. 
    Once you receive the command, use coinbase CDP toolkit to execute on-chain transactions.
    You have access to the following tools:
    - fetch_all_morpho_markets
    - fetch_vault_market_status
    - morpho_reallocate
    """.format(VAULT_ADDRESS)
)

