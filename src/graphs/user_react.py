from typing import TypedDict, Literal, Annotated, Sequence
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel
from config import Config
from utils import get_reallocation_tool, get_user_shares_tool
import json
from utils.market import fetch_all_morpho_markets, fetch_vault_market_status, VAULT_ADDRESS
from .model_util import get_llm, ModelType

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()


tools = [
    get_reallocation_tool(),
    get_user_shares_tool(),
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

executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False)

# use a ReAct node to automatically choose toolsl to execute transactions
react_agent = create_react_agent(
    executor_llm,
    tools=tools,
    checkpointer=memory,
    state_modifier="""Your name is Wowo, a manager of Morpho Vault, who give insights and analysis across different markets within the vault.
    You listen to the user message and give insights and analysis, or summary.

    You talk briefly, usually 2-3 sentences max, answer user question or handle the direct response to the user.  

    When you detect user deposits, you should greet them and welcome them to the vault

    The vault address is {}. 
    You have access to the following tools:
    - fetch_all_morpho_markets
    - fetch_vault_market_status
    - morpho_get_shares
    """.format(VAULT_ADDRESS),

)

