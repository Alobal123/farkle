from __future__ import annotations
from collections import defaultdict
from typing import Callable, Iterable, Optional
from game_event import GameEvent, GameEventType

class EventListener:
    """Central hub for publishing GameEvents to subscribed GameObjects or callbacks.

    Subscribers can optionally specify a set of GameEventType filters; if omitted they
    receive all events.
    """

    def __init__(self):
        # Map event type -> list[callable]
        self._subs_all: list[Callable[[GameEvent], None]] = []
        self._subs_specific: dict[GameEventType, list[Callable[[GameEvent], None]]] = defaultdict(list)
        # Simple reentrancy-safe queue so events published during a callback are processed afterward
        self._queue: list[GameEvent] = []
        self._dispatching: bool = False

    def subscribe(self, callback: Callable[[GameEvent], None], types: Optional[Iterable[GameEventType]] = None):
        if types is None:
            if callback not in self._subs_all:
                self._subs_all.append(callback)
        else:
            for t in types:
                lst = self._subs_specific[t]
                if callback not in lst:
                    lst.append(callback)

    def unsubscribe(self, callback: Callable[[GameEvent], None]):
        if callback in self._subs_all:
            self._subs_all.remove(callback)
        for lst in self._subs_specific.values():
            if callback in lst:
                lst.remove(callback)

    def publish(self, event: GameEvent):
        self._queue.append(event)
        if self._dispatching:
            return
        self._dispatching = True
        try:
            while self._queue:
                ev = self._queue.pop(0)
                # Dispatch to all-subscribers then type-specific
                for cb in list(self._subs_all):
                    try:
                        cb(ev)
                    except Exception:
                        pass
                for cb in list(self._subs_specific.get(ev.type, [])):
                    try:
                        cb(ev)
                    except Exception:
                        pass
        finally:
            self._dispatching = False
