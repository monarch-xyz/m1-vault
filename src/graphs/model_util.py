from typing import Literal
from config import Config
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


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
