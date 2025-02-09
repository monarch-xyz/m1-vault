from typing import Dict, List, Callable, Any

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    async def publish(self, event_type: str, data: Any = None):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                await callback(data)

__all__ = ['EventBus']