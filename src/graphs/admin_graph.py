from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal, Annotated, Sequence
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from langgraph.graph.message import add_messages
from pydantic import BaseModel
from config import Config
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
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
    intent: Literal["research", "action"]
    description: str

class State(TypedDict):
    # All messages, including user initial message.
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Interpretation results
    intent: Literal["research", "action"]
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

executor_llm = get_llm(Config.MODEL_TYPE, is_interpreter=False).bind_tools(tools)

async def interpret_message(state: State):
    """First node: Interpret the admin message and decide if it needs research or action"""
    
    router = interpreter_llm.with_structured_output(InterpretResult)
    result = router.invoke([
        SystemMessage(content="""
        You are an admin command interpreter. Determine if the message requires:
        - research: gathering information or analysis about market
        - action: any action related to CDP, tool use, manage wallet and executing on-chain transactions through CDP Agentkit.
        You have access to CDP Agentkit for managing a wallet and on-chain transactions.
        """),
        *state["messages"]
    ])
    
    return {
        "intent": result.intent,
        "description": result.description
    }

async def research_task(state: State):
    """Handle research-type requests with deep analysis"""

    context = morpho_knowledge_store.similarity_search(query=state["description"], k=5)

    response = await executor_llm.ainvoke([
        SystemMessage(
            content=f"You are a thorough DeFi researcher. Analyze the request and provide important information. \n\n Context: {context}"
        ),
        HumanMessage(content=f"Research request: {state['description']}")
    ])
    return {"messages": [response]}

async def action_task(state: State):
    """Handle action-type requests with precise execution"""
    response = await executor_llm.ainvoke([
        SystemMessage(content="You are an action executor. Explain what actions you would take and take action."),
        HumanMessage(content=f"Action request: {state['description']}")
    ])

    return {"messages": [response]}

def route_intent(state: State):
    """Route to either research or action based on intent"""
    return state["intent"]

def tool_node(state: State):
    outputs = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        outputs.append(
            ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": outputs}

# Run through model again to get final response
def call_model(state: State, config: RunnableConfig):
    response = executor_llm.invoke(state["messages"], config)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}

def create_admin_graph():
    """Create the admin command processing graph"""
    # start -> interpret -> [description] -> (research | action) -> [response] -> end

    # Initialize graph
    graph = StateGraph(State)
    
    # Add nodes
    graph.add_node("interpret", interpret_message)
    graph.add_node("research", research_task)
    graph.add_node("action", action_task)

    graph.add_node("tool", tool_node)
    graph.add_node("call_model", call_model)
    
    # Create edges
    graph.add_edge(START, "interpret")
    
    # Add conditional edges based on interpretation
    graph.add_conditional_edges(
        "interpret",
        route_intent,
        {
            "research": "research",
            "action": "action"
        }
    )
    
    # Connect both outcomes to END
    graph.add_edge("research", END)
    graph.add_edge("action", "tool")
    graph.add_edge("tool", "call_model")
    graph.add_edge("call_model", END)
    
    return graph.compile()