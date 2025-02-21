from datetime import datetime, timezone
from handlers.base_handler import BaseHandler
from models.events import EventType
from utils.market import get_all_market_history_summary, get_vault_allocations_summary
from utils.supabase import SupabaseClient
from langchain_core.messages import HumanMessage
from web3 import Web3
import os
from graphs.risk_react import react_agent

class PeriodicRiskHandler(BaseHandler):
    """Handler for periodic risk analysis"""
    
    def __init__(self, agent, logger):
        super().__init__(agent)
        self.logger = logger
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
            # Get consolidated market data
            market_stats_last_hour = await get_all_market_history_summary(self.web3, self.hours_ago)
            
            # Store snapshots
            for market in market_stats_last_hour:
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
            await self.analyze_risk(market_stats_last_hour)
            
        except Exception as e:
            await self.logger.error("PeriodicRiskHandler", f"Error in risk update: {str(e)}")

    async def analyze_risk(self, market_data):
        """Analyze market risk using LLM"""
        # Format data for LLM consumption
        market_summaries = []
        for market in market_data:
            summary = (
                f"Market {market['id']}:\n"
                f"Net Supply: {market['net_supply']/1e6:+,.2f} USDC "
                f"({market['net_supply']/market['total_supply']*100:+.1f}% change)\n"
                f"Net Borrow: {market['net_borrow']/1e6:+,.2f} USDC "
                f"({market['net_borrow']/market['total_borrow']*100:+.1f}% change)\n"
                f"Current APY - Supply: {market['supply_apy']:.2f}%, Borrow: {market['borrow_apy']:.2f}%"
            )
            market_summaries.append(summary)
        
        vault_allocation_summary = await get_vault_allocations_summary()

        prompt = f"""
        Here is the market activity in the last {self.hours_ago} hours:
        {market_summaries}

        Current Vault allocation
        {vault_allocation_summary}
        """
        
        state = await self.llm.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        }, config={"configurable": {"thread_id": "risk_analysis"}})

        # for all messages in state[messages], find things we want to print
        return state['messages'][-1].content