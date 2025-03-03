import time
import asyncio
import json
import os
import logging
from typing import Dict
from core.agent import Listener
from web3._utils.events import get_event_data
from web3.utils.abi import get_event_abi
from models.events import EventType, BaseEvent
from hexbytes import HexBytes
from web3 import Web3
from config import Config
from web3.contract import Contract

from models.messages import ChainMessage
from utils.constants import MORPHO_BLUE_ADDRESS, VAULT_ADDRESS


# Get the standard Python logger
logger = logging.getLogger(__name__)

MB_SUPPLY_TOPIC = "0xedf8870433c83823eb071d3df1caa8d008f12f6440918c20d75a3602cda30fe0"
MB_WITHDRAW_TOPIC = "0xa56fc0ad5702ec05ce63666221f796fb62437c32db1aa1aa075fc6484cf58fbf"
MB_BORROW_TOPIC = "0x570954540bed6b1304a87dfe815a5eda4a648f7097a16240dcd85c9b5fd42a43"
MB_REPAY_TOPIC = "0x52acb05cebbd3cd39715469f22afbf5a17496295ef3bc9bb5944056c63ccaa09"

# Todo: Change Vault to batch fetch from topic, if we need more events in the future
# MV_DEPOSIT_TOPIC = "0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7"

def get_event_abi_from_topic(abi: dict, topic0: HexBytes) -> dict:
    """Get the ABI for a specific event"""
    
    # convert hexbytes to hex string
    topic0 = "0x" + topic0.hex()

    # find according ABI for the specific event
    if topic0 == MB_SUPPLY_TOPIC:
        event_abi = get_event_abi(morpho_blue_abi, 'Supply')
    elif topic0 == MB_WITHDRAW_TOPIC:
        event_abi = get_event_abi(morpho_blue_abi, 'Withdraw')
    elif topic0 == MB_BORROW_TOPIC:
        event_abi = get_event_abi(morpho_blue_abi, 'Borrow')
    elif topic0 == MB_REPAY_TOPIC:
        event_abi = get_event_abi(morpho_blue_abi, 'Repay')
    else:
        logger.error(f"Unknown event type: {topic0}")
        return None

    return event_abi

class BaseEventProcessor:
    """Base class for contract-specific event processors"""
    def __init__(self, contract: Contract, event_bus, web3, polling_interval=10):
        self.contract = contract
        self.event_bus = event_bus
        self.web3 = web3
        self.event_types = []
        self.polling_interval = polling_interval
        self.is_running = False
        self.polling_task = None
        self.last_processed_block = 0

    async def start(self):
        """Start the processor's polling loop"""
        self.is_running = True
        self.polling_task = asyncio.create_task(self._poll_loop())
        logger.info(f"Starting processor {self.__class__.__name__}...")

    async def stop(self):
        """Stop the processor's polling loop"""
        logger.info(f"Stopping processor {self.__class__.__name__}...")
        self.is_running = False
        
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
            self.polling_task = None

    async def _poll_loop(self):
        """Block polling for this processor"""
        while self.is_running:
            try:
                latest_block = self.web3.eth.block_number
                
                # when we restart, scan back 10 blocks
                if self.last_processed_block == 0:
                    self.last_processed_block = latest_block - 10

                if latest_block > self.last_processed_block:
                    await self.process_blocks(
                        from_block=self.last_processed_block + 1,
                        to_block=latest_block
                    )
                    self.last_processed_block = latest_block
                
                await asyncio.sleep(self.polling_interval)
                
            except asyncio.CancelledError:
                break  # Handle cancellation
            except Exception as e:
                logger.error(f"{self.__class__.__name__} Polling Error: {str(e)}")
                await asyncio.sleep(self.polling_interval)

    async def process_blocks(self, from_block: int, to_block: int):
        """Process events in block range (to be implemented per contract)"""
        raise NotImplementedError

def load_abi(filename: str) -> dict:
    """Load ABI from json file"""
    path = os.path.join(os.path.dirname(__file__), '..', 'abi', filename)
    with open(path) as f:
        return json.load(f)

morpho_blue_abi = load_abi('morpho-blue.json')
morpho_vault_abi = load_abi('morpho-vault.json')

class OnChainListener(Listener):
    """Shared block polling with multiple contract processors"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.processors: Dict[str, BaseEventProcessor] = {}
        
        # Initialize Web3
        self.web3 = Web3(Web3.HTTPProvider(Config.CHAIN_RPC_URL))

        # Initialize contracts
        morpho_blue_contract = self.web3.eth.contract(
            address=MORPHO_BLUE_ADDRESS,
            abi=morpho_blue_abi
        )
        vault_contract = self.web3.eth.contract(
            address=VAULT_ADDRESS,
            abi=morpho_vault_abi
        )

        # Initialize processors with different polling intervals
        self.add_processor(
            "morpho_blue",
            MorphoBlueProcessor(morpho_blue_contract, event_bus, self.web3, polling_interval=60)
        )
        self.add_processor(
            "morpho_vault",
            MorphoVaultProcessor(vault_contract, event_bus, self.web3, polling_interval=15)
        )
    
    def add_processor(self, name: str, processor: BaseEventProcessor):
        """Add a contract event processor"""
        self.processors[name] = processor

    async def start(self):
        """Start all processors"""
        logger.info("Starting onchain listener...")
        for name, processor in self.processors.items():
            await processor.start()
    
    async def stop(self):
        """Stop all processors and cleanup"""
        logger.info("Stopping onchain listener...")
        stop_tasks = [processor.stop() for processor in self.processors.values()]
        await asyncio.gather(*stop_tasks)
        logger.info("Onchain listener stopped")

    # _poll_loop and _process_new_blocks methods are now removed as they're moved to BaseEventProcessor

# Example processor implementations
class MorphoBlueProcessor(BaseEventProcessor):
    """Process MorphoBlue lending market events"""
    
    def __init__(self, contract, event_bus, web3, polling_interval=60):
        super().__init__(contract, event_bus, web3, polling_interval)
    
    async def process_blocks(self, from_block: int, to_block: int):
        # Get all relevant events in one batch
        print(f"MorphoBlue: Processing blocks {from_block} to {to_block}")

        event_filter = self.web3.eth.filter({
            "address": MORPHO_BLUE_ADDRESS,
            "topics": [[
                # Topic 0 = Supply OR Withdraw OR Borrow OR Repay
                MB_SUPPLY_TOPIC,
                MB_WITHDRAW_TOPIC,
                MB_BORROW_TOPIC,
                MB_REPAY_TOPIC
            ]],
            "fromBlock": from_block,
            "toBlock": to_block
        })
        events = event_filter.get_all_entries()

        # Process and publish events
        for raw_log in events:
            # find according ABI for the specific event
            event_abi = get_event_abi_from_topic(morpho_blue_abi, raw_log['topics'][0])
            log = get_event_data(self.web3.codec, event_abi, raw_log)

            try:
                data = self._parse_event(log)
                # We need to publish with event type and event data separately

                event = BaseEvent(
                    type=EventType.CHAIN_EVENT,
                    data=data,
                    source="morpho_blue",
                    timestamp=time.time()
                )

                print("Publishing event", event)

                await self.event_bus.publish(EventType.CHAIN_EVENT, event)
            except Exception as e:
                logger.error("MorphoBlue", str(e))

    def _parse_event(self, log):
        evm_event_type = log.event.lower()  # supply, withdraw, repay, borrow
        parsed = dict(log.args)

        # Convert bytes to hex string for market_id
        market_id = parsed.get('id', b'').hex() if isinstance(parsed.get('id'), bytes) else ''
        
        return {
            'evm_event': evm_event_type,
            'tx_hash': log.transactionHash.hex(),
            'market_id': market_id,
            'caller': parsed.get('caller', ''),
            'on_behalf': parsed.get('onBehalf', ''),
            'receiver': parsed.get('receiver', ''),
            'assets': str(parsed.get('assets', 0)),
            'shares': str(parsed.get('shares', 0)),
            'source': "morpho_blue",
            'timestamp': int(time.time())
        }

class MorphoVaultProcessor(BaseEventProcessor):
    """Process Morpho Vault deposit events"""
    
    def __init__(self, contract, event_bus, web3, polling_interval=10):
        super().__init__(contract, event_bus, web3, polling_interval)
    
    async def process_blocks(self, from_block: int, to_block: int):
        print(f"MorphoVault: Processing blocks {from_block} to {to_block}")
        deposit_events = self.contract.events.Deposit().get_logs(from_block=from_block, to_block=to_block)
        
        for log in deposit_events:
            # parse deposit event and set as "CHAIN_EVENT" event
            try:
                data = self._parse_event(log)
                event = BaseEvent(
                    type=EventType.CHAIN_EVENT,
                    data=data,
                    source="morpho_vault",
                    timestamp=time.time()
                )
                await self.event_bus.publish(EventType.CHAIN_EVENT, event)
            except Exception as e:
                print(f"[MorphoVault] Event process error: {str(e)}")

            # Parse attached bytes as user message
            try:
                txhash = log.transactionHash.hex()
                
                # Try to get the transaction with retries
                tx = None
                retries = 5
                while retries > 0 and not tx:
                    try:
                        tx = self.web3.eth.get_transaction(txhash)
                    except Exception:
                        retries -= 1
                        if retries > 0:  # Only sleep if we're going to retry
                            await asyncio.sleep(5)
                
                if not tx:
                    print(f"[MorphoVault] No transaction found for {txhash}")
                    return

                # Extract and decode message
                input_data = tx['input']
                if len(input_data) <= 68:  # No message attached
                    return
                    
                # Convert HexBytes to string and remove '0x' prefix
                if hasattr(input_data, 'hex'):
                    message_hex = input_data[68:].hex()
                else:
                    message_hex = input_data[68:]
                    if message_hex.startswith('0x'):
                        message_hex = message_hex[2:]
                
                try:
                    # Try to decode as UTF-8 string
                    message_bytes = bytes.fromhex(message_hex)
                    message = message_bytes.decode('utf-8').strip()
                    
                    if message:  # Only process non-empty messages
                        logger.info(f"[MorphoVault] Decoded message: {message}")
                        
                        data = ChainMessage(
                            text=message,
                            sender=tx['from'],
                            transaction_hash=txhash,
                            timestamp=time.time()
                        )

                        # publish user message
                        event = BaseEvent(
                            type=EventType.USER_MESSAGE,
                            data=data,
                            source="onchain",
                            timestamp=time.time()
                        )
                        await self.event_bus.publish(EventType.USER_MESSAGE, event)

                except (UnicodeDecodeError, ValueError) as e:
                    logger.error(f"[MorphoVault] Message decode error: {str(e)}")

            except Exception as e:
                logger.error(f"[MorphoVault] Error: {str(e)}")

    def _parse_event(self, log):
        parsed = dict(log.args)
        
        return {
            'protocol': 'morpho_vault',
            'evm_event': 'deposit',
            'tx_hash': log.transactionHash.hex(),
            'sender': parsed.get('sender', ''),
            'owner': parsed.get('owner', ''),
            'assets': str(parsed.get('assets', 0)),
            'shares': str(parsed.get('shares', 0)),
            'source': "morpho_vault",
            'timestamp': int(time.time())
        } 