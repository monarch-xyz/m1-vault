from datetime import datetime, timezone
from handlers.base_handler import BaseHandler
from models.events import EventType
from utils.market import get_all_market_history, format_market_history, get_vault_allocations_summary
from utils.supabase import SupabaseClient
from utils.activity_types import PERIODIC_ANALYSIS_STARTED, PERIODIC_ANALYSIS_COMPLETED
from langchain_core.messages import HumanMessage
from web3 import Web3
import os
from graphs.risk_react import react_agent
import logging

# Get the standard Python logger
logger = logging.getLogger(__name__)

class PeriodicRiskHandler(BaseHandler):
    """Handler for periodic risk analysis"""
    
    def __init__(self, agent):
        super().__init__(agent)
        # Initialize Web3
        self.web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.hours_ago = 1
        self.llm = react_agent
    
    @property
    def subscribes_to(self):
        return [EventType.RISK_UPDATE]

    async def handle(self, event):
        """Handle periodic risk update events"""
        try:
            # Broadcast analysis start
            await self.agent.broadcast_activity(PERIODIC_ANALYSIS_STARTED, {
                "interval_hours": self.hours_ago,
                "timestamp": datetime.now().timestamp()
            })

            # Get consolidated market data
            market_summaries = await get_all_market_history(self.web3, self.hours_ago)
            
            # Store snapshots
            for market in market_summaries:
                snapshot = {
                    'market': market['id'],
                    'interval': self.hours_ago * 3600,
                    'total_supply': int(market['total_supply']),
                    'total_borrow': int(market['total_borrow']),
                    'supply': int(market['supply']),
                    'borrow': int(market['borrow']),
                    'withdraw': int(market['withdraw']),
                    'repay': int(market['repay'])
                }
                await SupabaseClient.store_market_snapshot(snapshot)
            
            # Pass data to risk analysis
            result = await self.analyze_risk(market_summaries)
            
            # Broadcast analysis completion
            await self.agent.broadcast_activity(PERIODIC_ANALYSIS_COMPLETED, {
                "interval_hours": self.hours_ago,
                "report_length": len(result) if result else 0
            })
            
        except Exception as e:
            logger.error(f"PeriodicRiskHandler: Error in risk update: {str(e)}")
            
    async def analyze_risk(self, market_data):
        """Analyze market risk using LLM"""
        # Format data for LLM consumption
        market_history_summary = await format_market_history(market_data)
        
        vault_allocation_summary = await get_vault_allocations_summary()

        prompt = f"""
        [Automated Trigger Message]
        Here is the market activity in the last {self.hours_ago} hours:
        {market_history_summary}

        Current Vault allocation
        {vault_allocation_summary}
        """
        
        state = await self.llm.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        }, config={"configurable": {"thread_id": "risk_analysis"}})

        # for all messages in state[messages], find things we want to print
        content = state['messages'][-1].content
        await SupabaseClient.store_report("hourly",content)

        return content