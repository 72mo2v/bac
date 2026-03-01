import asyncio
from typing import Callable, Dict, List, Any

class EventDispatcher:
    def __init__(self):
        # event_name -> list of subscribers
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)

    async def dispatch(self, event_name: str, **kwargs):
        if event_name not in self.subscribers:
            return
        
        tasks = []
        for callback in self.subscribers[event_name]:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(**kwargs))
            else:
                callback(**kwargs)
        
        if tasks:
            await asyncio.gather(*tasks)

event_dispatcher = EventDispatcher()
