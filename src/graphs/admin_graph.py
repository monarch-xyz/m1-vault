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
from utils import setup_cdp_toolkit
import json

tools = setup_cdp_toolkit()
tools_by_name = {tool.name: tool for tool in tools}

# Initialize the vector store
# Todo: use different vector store for different types of knowledges
morpho_knowledge_store = Chroma(
    collection_name="morpho_knowledge",
    embedding_function=OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY),
    persist_directory="data/morpho_knowledge",
)

# Define our models
class InterpretResult(BaseModel):
    intent: Literal["morpho", "action"]
    description: str

class State(TypedDict):
    # All messages, including user initial message.
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Interpretation results
    intent: Literal["morpho", "action"]
    description: str
    
    # Todo: Add more states here for different nodes to share data, for example building transactions.

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

# Initialize LLMs with configurable model type
interpreter_llm = get_llm(Config.MODEL_TYPE, is_interpreter=True)

executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False)

# use a ReAct node to automatically choose toolsl to execute transactions
react_agent = create_react_agent(
    executor_llm,
    tools=tools,
    state_modifier="""You are an Morpho Vault reallocator. Once you receive the command, use coinbase CDP toolkit to execute on-chain transactions.
    You have access to the following tools:
    - get_balance
    - get_wallet_details
    - transfer
    - morpho_deposit
    - morpho_withdraw
    - morpho_is_allocator
    - morpho_reallocate
    """
)

async def interpret_message(state: State):
    """First node: Interpret the admin message and decide if it needs morpho or action"""
    
    router = interpreter_llm.with_structured_output(InterpretResult)
    result = router.invoke([
        SystemMessage(content="""
        You are an admin command interpreter. Determine if the message requires:
        - morpho: Answer question about Morpho protocol, vaults ...etc, that could be answered by documents in the knowledge base.
        - action: any action related to wallet / account balance / specific morpho vault and tools to executing on-chain transactions through CDP Agentkit.
        """),
        *state["messages"]
    ])

    return {
        "intent": result.intent,
        "description": result.description
    }

async def answer_morpho_question(state: State):
    """Handle morpho-type requests with deep analysis"""

    context = morpho_knowledge_store.similarity_search(query=state["description"], k=5)

    response = await executor_llm.ainvoke([
        SystemMessage(
            content=f"You are a thorough DeFi researcher. Analyze the request and provide important information. \n\n Context: {context}"
        ),
        HumanMessage(content=f"Research request: {state['description']}")
    ])
    return {"messages": [response]}


async def action_task(state: State):
    """Handle action-type requests with on-chain transactions"""
    response = react_agent.invoke({"messages": state["messages"]})
    # React Model returns their own state, we only need messages
    return {"messages": [response["messages"][-1]]}


def route_intent(state: State):
    """Route to either morpho or action based on intent"""
    return state["intent"]


def create_admin_graph():
    """Create the admin command processing graph"""
    # start -> interpret -> [description] -> (morpho | action) -> [response] -> end

    # Initialize graph
    graph = StateGraph(State)
    
    # Add nodes
    graph.add_node("interpret", interpret_message)
    graph.add_node("morpho", answer_morpho_question)
    graph.add_node("action", action_task)

    
    # Create edges
    graph.add_edge(START, "interpret")
    
    # Add conditional edges based on interpretation
    graph.add_conditional_edges(
        "interpret",
        route_intent,
        {
            "morpho": "morpho",
            "action": "action"
        }
    )
    
    # Connect both outcomes to END
    graph.add_edge("morpho", END)
    graph.add_edge("action", END)
    
    return graph.compile()