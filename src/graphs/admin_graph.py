from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from config import Config

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
    
    # Final output
    response: str

# Initialize LLMs - using different models for different purposes
interpreter_llm = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    api_key=Config.ANTHROPIC_API_KEY
)

executor_llm = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    api_key=Config.ANTHROPIC_API_KEY
)

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
    response = await executor_llm.ainvoke([
        SystemMessage(content="You are a thorough researcher. Analyze the request and provide detailed information."),
        HumanMessage(content=f"Research request: {state['description']}")
    ])
    
    return {"response": response.content}

async def action_task(state: State):
    """Handle action-type requests with precise execution"""
    response = await executor_llm.ainvoke([
        SystemMessage(content="You are an action executor. Explain what actions you would take."),
        HumanMessage(content=f"Action request: {state['description']}")
    ])
    
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