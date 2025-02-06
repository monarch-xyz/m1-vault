"""CDP toolkit integration module."""
import os
import logging
from typing import Optional, Tuple
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

logger = logging.getLogger(__name__)

def setup_cdp_toolkit():
    """Initialize CDP toolkit with credentials from environment."""
    try:
        cdp_wrapper = CdpAgentkitWrapper(
            cdp_api_key_name=os.getenv("CDP_API_KEY_NAME"),
            cdp_api_key_private_key=os.getenv("CDP_API_PRIVATE_KEY"),
            network_id=os.getenv("NETWORK_ID"),
            mnemonic_phrase=os.getenv("MNEMONIC_PHRASE"),
        )
        cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(cdp_wrapper)
        logger.info("CDP toolkit initialized successfully.")
        return cdp_toolkit.get_tools()
    except ValueError as e:
        logger.error(f"Failed to initialize CDP toolkit: {str(e)}")
        return None