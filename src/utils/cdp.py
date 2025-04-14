import os

from coinbase_agentkit import (
    AgentKit,
    AgentKitConfig,
    EthAccountWalletProvider,
    EthAccountWalletProviderConfig,
    twitter_action_provider,
)

from eth_account import Account

Account.enable_unaudited_hdwallet_features()

account = Account.from_mnemonic(os.getenv("MNEMONIC_PHRASE"))

wallet_provider = EthAccountWalletProvider(
    config=EthAccountWalletProviderConfig(
        account=account,
        chain_id="8453",
        rpc_url=os.getenv("RPC_URL")
    )
)

from coinbase_agentkit_langchain import get_langchain_tools
from .action_provider import morpho_action_provider

agent_kit = AgentKit(AgentKitConfig(
    wallet_provider=wallet_provider,
    action_providers=[
        morpho_action_provider(),
        twitter_action_provider()
    ]
))

cdp_tools = get_langchain_tools(agent_kit)

read_only_tools = [tool for tool in cdp_tools if "get_shares" in tool.name]

