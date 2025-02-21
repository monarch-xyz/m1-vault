from core.agent import Listener
from models.events import EventType, BaseEvent
import asyncio
from datetime import datetime

class TimerListener(Listener):
    """Emits periodic events for scheduled tasks"""
    
    def __init__(self, event_bus, logger):
        super().__init__(event_bus, logger)
        self.is_running = False
        self.tasks = []
        self.intervals = {
            'RISK_UPDATE': 600  # seconds
        }

    async def start(self):
        """Start timer-based event emission"""
        self.is_running = True
        self.tasks.append(
            asyncio.create_task(self._emit_risk_events())
        )
        await self.logger.action("TimerListener", "Timer-based event emission started")

    async def stop(self):
        """Stop all timers"""
        self.is_running = False
        for task in self.tasks:
            task.cancel()
        self.tasks = []
        await self.logger.action("TimerListener", "Timer-based event emission stopped")

    async def _emit_risk_events(self):
        """Emit periodic risk update events"""
        while self.is_running:
            try:
                # Create and emit event
                event = BaseEvent(
                    type=EventType.RISK_UPDATE,
                    data={
                        'type': 'periodic_update'
                    },
                    source="timer",
                    timestamp=datetime.now().timestamp()
                )
                
                await self.event_bus.publish(EventType.RISK_UPDATE, event)
                
            except Exception as e:
                await self.logger.error("TimerListener", f"Error emitting risk event: {str(e)}")
            
            # Wait for next interval
            await asyncio.sleep(self.intervals['RISK_UPDATE']) 