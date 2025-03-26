import os

from coinbase_agentkit import (
    AgentKit,
    AgentKitConfig,
    CdpWalletProvider,
    CdpWalletProviderConfig,
    twitter_action_provider,
)

from coinbase_agentkit_langchain import get_langchain_tools
from .action_provider import morpho_action_provider

wallet_provider = CdpWalletProvider(CdpWalletProviderConfig(
    mnemonic_phrase=os.getenv("MNEMONIC_PHRASE"),
    network_id=os.getenv("NETWORK_ID")
))

agent_kit = AgentKit(AgentKitConfig(
    wallet_provider=wallet_provider,
    action_providers=[
        morpho_action_provider(),
        twitter_action_provider()
    ]
))

cdp_tools = get_langchain_tools(agent_kit)

read_only_tools = [tool for tool in cdp_tools if "get_shares" in tool.name]

