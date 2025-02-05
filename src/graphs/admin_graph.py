from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from config import Config
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

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
    # Input from handler
    message: str
    
    # Interpretation results
    intent: Literal["research", "action"]
    description: str
    
    # Todo: Add more states here for different nodes to share data, for example building transactions.

    # Final output
    response: str

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

async def interpret_message(state: State):
    """First node: Interpret the admin message and decide if it needs research or action"""
    
    router = interpreter_llm.with_structured_output(InterpretResult)
    result = router.invoke([
        SystemMessage(content="""
        You are an admin command interpreter. Determine if the message requires:
        - research: gathering information or analysis
        - action: executing on-chain transactions
        """),
        HumanMessage(content=state["message"])
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
    
    return {"response": response.content}

async def action_task(state: State):
    """Handle action-type requests with precise execution"""
    response = await executor_llm.ainvoke([
        SystemMessage(content="You are an action executor. Explain what actions you would take."),
        HumanMessage(content=f"Action request: {state['description']}")
    ])

    # todo: execute the transaction, simulations... etc, or -- connect to another graph!
    
    return {"response": response.content}

def route_intent(state: State):
    """Route to either research or action based on intent"""
    return state["intent"]

def create_admin_graph():
    """Create the admin command processing graph"""
    
    # Initialize graph
    graph = StateGraph(State)
    
    # Add nodes
    graph.add_node("interpret", interpret_message)
    graph.add_node("research", research_task)
    graph.add_node("action", action_task)
    
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
    graph.add_edge("action", END)
    
    return graph.compile() 