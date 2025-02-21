from datetime import datetime, timezone
from collections import defaultdict
from handlers.base_handler import BaseHandler
from models.events import EventType
from utils.supabase import SupabaseClient
from utils.market import MarketReader
from web3 import Web3
import os

class PeriodicRiskHandler(BaseHandler):
    """Handler for periodic risk analysis"""
    
    def __init__(self, agent, logger):
        super().__init__(agent)
        self.logger = logger
        # Initialize Web3 and MarketReader
        self.web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.market_reader = MarketReader(self.web3)
        self.hours_ago = 1

    @property
    def subscribes_to(self):
        return [EventType.RISK_UPDATE]

    async def handle(self, event):
        """Handle periodic risk update events"""
        try:
            # Fetch market events
            market_events = await SupabaseClient.get_filtered_market_events(hours_ago=self.hours_ago)
            print('market_events', len(market_events))
            
            # Calculate operations
            data = self.calculate_market_operations(market_events)
            if not data:
                return

            # Print overall summary
            summary = self.format_summary(data)
            print("[PeriodicRiskHandler] Summary:\n", summary)

            # Process each market
            for market in data['breakdown']:
                # Get on-chain data
                market_stats = await self.market_reader.get_market_data(market['id'])
                if not market_stats:
                    continue
                    
                # Format market details
                market_summary = self.format_market(market, market_stats)
                if market_summary:  # Only print if there's activity
                    print(market_summary)
                
                # Store snapshot
                snapshot = {
                    'market': market['id'],
                    'interval': self.hours_ago * 3600,
                    'total_supply': int(market_stats['supply_assets']),
                    'total_borrow': int(market_stats['borrow_assets']),
                    'supply': int(market['supply']),
                    'borrow': int(market['borrow']),
                    'withdraw': int(market['withdraw']),
                    'repay': int(market['repay'])
                }
                await SupabaseClient.store_market_snapshot(snapshot)
            
        except Exception as e:
            await self.logger.error("PeriodicRiskHandler", f"Error in risk update: {str(e)}")

    @staticmethod
    def calculate_market_operations(market_events):
        """Calculate operation stats from morpho market events"""
        if not market_events:
            return None
            
        # Initialize accumulators
        accumulated = {
            'borrow': 0,
            'supply': 0,
            'withdraw': 0,
            'repay': 0
        }
        
        # Initialize market breakdown
        markets = defaultdict(lambda: {
            'id': '',
            'borrow': 0,
            'supply': 0,
            'withdraw': 0,
            'repay': 0
        })
        
        # Process events
        for event in market_events:
            op_type = event['event']
            amount = float(event['amount']) if event['amount'] else 0
            market_id = event['market']

            # skip wrong data with wrong types
            if not op_type or not amount or not market_id:
                continue
            
            # Update accumulated totals
            if op_type in accumulated:
                accumulated[op_type] += amount
            
            # Update market breakdown
            if market_id:
                markets[market_id]['id'] = market_id
                markets[market_id][op_type] += amount

        return {
            'accumulated': accumulated,
            'breakdown': list(markets.values())
        }

    def format_summary(self, data):
        """Format overall summary of operations"""
        if not data:
            return "No market operations detected in this period."
        
        summary_lines = ["All Markets Operations Summary:"]
        
        # Add accumulated totals
        total_net_supply = 0
        total_net_borrow = 0
        
        for market in data['breakdown']:
            total_net_supply += market['supply'] - market['withdraw']
            total_net_borrow += market['borrow'] - market['repay']
        
        if total_net_supply != 0:
            sign = '+' if total_net_supply > 0 else ''
            summary_lines.append(
                f"Total Net Supply: {sign}{total_net_supply/1e6:,.2f} USDC"
            )
            
        if total_net_borrow != 0:
            sign = '+' if total_net_borrow > 0 else ''
            summary_lines.append(
                f"Total Net Borrow: {sign}{total_net_borrow/1e6:,.2f} USDC"
            )
            
        return "\n".join(summary_lines)

    def format_market(self, market_data, market_stats):
        """
        Format single market operations with on-chain stats
        
        Args:
            market_data: Dict with supply/borrow/withdraw/repay volumes
            market_stats: Dict with total_supply and total_borrow from chain
        """
        market_id = market_data['id']
        
        # Calculate net movements
        net_supply = market_data['supply'] - market_data['withdraw']
        net_borrow = market_data['borrow'] - market_data['repay']
        
        # Skip markets with no activity
        if net_supply == 0 and net_borrow == 0:
            return None
            
        total_supply = market_stats['supply_assets']
        total_borrow = market_stats['borrow_assets']
        
        # Calculate percentages
        supply_change_pct = (net_supply / total_supply * 100) if total_supply > 0 else 0
        borrow_change_pct = (net_borrow / total_borrow * 100) if total_borrow > 0 else 0
        
        lines = [f"\nMarket {market_id}:"]
        
        # Supply/Withdraw summary
        if net_supply != 0:
            net_supply_usdc = net_supply / 1e6
            sign = '+' if net_supply > 0 else ''
            lines.append(
                f"Net Supply: {sign}{net_supply_usdc:,.2f} USDC ({sign}{supply_change_pct:.1f}% of total)"
            )
            if market_data['supply'] > 0 and market_data['withdraw'] > 0:
                lines.append(
                    f"- Supply: +{market_data['supply']/1e6:,.2f} USDC"
                    f"- Withdraw: -{market_data['withdraw']/1e6:,.2f} USDC"
                )
        
        # Borrow/Repay summary
        if net_borrow != 0:
            net_borrow_usdc = net_borrow / 1e6
            sign = '+' if net_borrow > 0 else ''
            lines.append(
                f"Net Borrow: {sign}{net_borrow_usdc:,.2f} USDC ({sign}{borrow_change_pct:.1f}% of total)"
            )
            if market_data['borrow'] > 0 and market_data['repay'] > 0:
                lines.append(
                    f"- Borrow: +{market_data['borrow']/1e6:,.2f} USDC"
                    f"- Repay: -{market_data['repay']/1e6:,.2f} USDC"
                )
        
        # Market state
        lines.append(
            f"Market State: {total_supply/1e6:,.2f} USDC supplied, "
            f"{total_borrow/1e6:,.2f} USDC borrowed"
        )
        
        return "\n".join(lines) 