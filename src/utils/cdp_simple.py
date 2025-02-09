from typing import Any, Callable
from pydantic import BaseModel
from web3 import Web3
import os
from cdp import Wallet, MnemonicSeedPhrase, Cdp

class CDPClient:
    """Simplified CDP client for direct transaction handling."""
    
    def __init__(self):
        self.wallet = self._initialize_wallet()
        
    def _initialize_wallet(self):
        """Initialize wallet with environment variables."""

        pk = os.getenv("CDP_API_PRIVATE_KEY").replace("\\n", "\n")

        # Configure CDP
        Cdp.configure(
            api_key_name=os.getenv("CDP_API_KEY_NAME"),
            private_key=pk
        )
        
        # Initialize wallet
        mnemonic = os.getenv("MNEMONIC_PHRASE")
        network_id = os.getenv("NETWORK_ID", "base-sepolia")
        
        if mnemonic:
            return Wallet.import_wallet(MnemonicSeedPhrase(mnemonic), network_id)
        return Wallet.create(network_id)

    def send_transaction(self, contract_address: str, abi: list, method: str, args: dict) -> str:
        """Directly send a contract transaction."""
        tx = self.wallet.invoke_contract(
            contract_address=Web3.to_checksum_address(contract_address),
            method=method,
            abi=abi,
            args=args
        )
        return str(tx.hash)

class CDPTool:
    """Simplified tool wrapper for CDP actions."""
    
    def __init__(self, client: CDPClient, func: Callable, schema: type[BaseModel] = None):
        self.client = client
        self.func = func
        self.args_schema = schema

    def run(self, **kwargs) -> str:
        """Execute the tool with validated arguments."""
        if self.args_schema:
            validated = self.args_schema(**kwargs).model_dump()
        else:
            validated = kwargs
            
        return self.func(self.client, **validated) 