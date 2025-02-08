from typing import Dict
from core.agent import Listener
from models.events import EventType, BaseEvent
import time
import asyncio
from web3 import Web3
from config import Config
from web3.contract import Contract
import json
import os

class BaseEventProcessor:
    """Base class for contract-specific event processors"""
    def __init__(self, contract: Contract, event_bus, logger):
        self.contract = contract
        self.event_bus = event_bus
        self.logger = logger
        self.event_types = []  # ['Deposit', 'Withdraw']

    def process_blocks(self, from_block: int, to_block: int):
        """Process events in block range (to be implemented per contract)"""
        raise NotImplementedError

def load_abi(filename: str) -> dict:
    """Load ABI from json file"""
    path = os.path.join(os.path.dirname(__file__), '..', 'abi', filename)
    with open(path) as f:
        return json.load(f)

class OnChainListener(Listener):
    """Shared block polling with multiple contract processors"""
    
    def __init__(self, event_bus, logger):
        self.event_bus = event_bus
        self.logger = logger
        
        # Initialize Web3
        self.web3 = Web3(Web3.HTTPProvider(Config.CHAIN_RPC_URL))
        self.processors: Dict[str, BaseEventProcessor] = {}
        self.last_processed_block = 0

        # Load contract ABIs
        morpho_blue_abi = load_abi('morpho-blue.json')
        morpho_vault_abi = load_abi('morpho-vault.json')

        # Initialize contracts
        morpho_blue_contract = self.web3.eth.contract(
            address='0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb',
            abi=morpho_blue_abi
        )
        vault_contract = self.web3.eth.contract(
            address='0x346AAC1E83239dB6a6cb760e95E13258AD3d1A6d',
            abi=morpho_vault_abi
        )

        # Initialize processors
        self.add_processor(
            "morpho_blue",
            MorphoBlueProcessor(morpho_blue_contract, event_bus, logger)
        )
        self.add_processor(
            "morpho_vault",
            MorphoVaultProcessor(vault_contract, event_bus, logger)
        )
    
    def add_processor(self, name: str, processor: BaseEventProcessor):
        """Add a contract event processor"""
        self.processors[name] = processor

    async def start(self):
        await self.logger.action("OnChainListener", "Starting block polling...")
        asyncio.create_task(self._poll_loop())
    
    async def _poll_loop(self):
        """Shared block polling for all processors"""
        while True:
            try:
                latest_block = self.web3.eth.block_number
                
                # when we restart, scan back 10 blocks
                if self.last_processed_block == 0:
                    self.last_processed_block = latest_block - 10

                if latest_block > self.last_processed_block:
                    await self._process_new_blocks(
                        from_block=self.last_processed_block + 1,
                        to_block=latest_block
                    )
                    self.last_processed_block = latest_block
                
                await asyncio.sleep(60)
                
            except Exception as e:
                await self.logger.error("BlockPolling", str(e))
                await asyncio.sleep(60)

    async def _process_new_blocks(self, from_block: int, to_block: int):
        """Notify all processors about new block range"""
        for name, processor in self.processors.items():
            try:
                processor.process_blocks(from_block, to_block)
            except Exception as e:
                await self.logger.error(f"Processor_{name}", str(e))

    async def stop(self):
        await self.logger.event("OnChainListener", "Stopping block polling...")

    def _parse_event(self, raw_event) -> BaseEvent:
        # Implement event parsing logic
        return BaseEvent(
            type=EventType.USER_MESSAGE,
            data=raw_event,
            source="blockchain",
            timestamp=time.time()
        )

# Example processor implementations
class MorphoBlueProcessor(BaseEventProcessor):
    """Process MorphoBlue lending market events"""
    
    def process_blocks(self, from_block: int, to_block: int):
        # Get all relevant events in one batch
        supply_events = self.contract.events.Supply().get_logs(from_block=from_block, to_block=to_block)
        withdraw_events = self.contract.events.Withdraw().get_logs(from_block=from_block, to_block=to_block)
        repay_events = self.contract.events.Repay().get_logs(from_block=from_block, to_block=to_block)
        borrow_events = self.contract.events.Borrow().get_logs(from_block=from_block, to_block=to_block)

        # Process and publish events
        for log in supply_events + withdraw_events + repay_events + borrow_events:
            try:
                event = self._parse_event(log)
                self.event_bus.publish(event)
            except Exception as e:
                self.logger.error(f"Error processing MorphoBlue event: {str(e)}")

    def _parse_event(self, log):
        evm_event_type = log.event.lower()  # supply, withdraw, repay, borrow
        parsed = dict(log.args)
        
        return BaseEvent(
            type=EventType.CHAIN_EVENT,
            data={
                'protocol': 'morpho_blue',
                'evm_event': evm_event_type,
                'tx_hash': log.transactionHash.hex(),
                'block_number': log.blockNumber,
                'market_id': parsed.get('id', b'').hex(),
                'caller': parsed.get('caller', ''),
                'on_behalf': parsed.get('onBehalf', ''),
                'receiver': parsed.get('receiver', ''),
                'assets': str(parsed.get('assets', 0)),
                'shares': str(parsed.get('shares', 0))
            },
            source="morpho_blue",
            timestamp=int(time.time())
        )

class MorphoVaultProcessor(BaseEventProcessor):
    """Process Morpho Vault deposit events"""
    
    def process_blocks(self, from_block: int, to_block: int):
        deposit_events = self.contract.events.Deposit().get_logs(from_block=from_block, to_block=to_block)
        
        for log in deposit_events:
            try:
                event = self._parse_event(log)
                self.event_bus.publish(event)
            except Exception as e:
                self.logger.error(f"Error processing Vault deposit: {str(e)}")

    def _parse_event(self, log):
        parsed = dict(log.args)
        
        return BaseEvent(
            type=EventType.CHAIN_EVENT,
            data={
                'protocol': 'morpho_vault',
                'evm_event': 'deposit',
                'tx_hash': log.transactionHash.hex(),
                'block_number': log.blockNumber,
                'sender': parsed.get('sender', ''),
                'owner': parsed.get('owner', ''),
                'assets': str(parsed.get('assets', 0)),
                'shares': str(parsed.get('shares', 0))
            },
            source="morpho_vault",
            timestamp=int(time.time())
        ) 