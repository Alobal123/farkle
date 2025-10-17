"""Shared test utilities for the Farkle project."""
from __future__ import annotations
from typing import List
from game_event import GameEvent, GameEventType

class EventCollector:
    """Simple event sink used in tests to capture published GameEvents.

    Usage:
        collector = EventCollector()
        game.event_listener.subscribe(collector.on_event)
        # ... run code ...
        types = [e.type for e in collector.events]
    """
    def __init__(self) -> None:
        self.events: List[GameEvent] = []
    def on_event(self, event: GameEvent):
        self.events.append(event)
    def types(self) -> List[GameEventType]:
        return [e.type for e in self.events]
    def clear(self):
        self.events.clear()

__all__ = ["EventCollector"]
