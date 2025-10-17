import pygame
from typing import Protocol, Optional

class Screen(Protocol):
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...
    def draw(self, surface: pygame.Surface) -> None: ...
    def is_done(self) -> bool: ...
    def next_screen(self) -> Optional[str]: ...

class SimpleScreen:
    """Minimal concrete base class implementing done/next logic."""
    def __init__(self):
        self._done = False
        self._next: Optional[str] = None
    def handle_event(self, event: pygame.event.Event) -> None: pass
    def update(self, dt: float) -> None: pass
    def draw(self, surface: pygame.Surface) -> None: pass
    def is_done(self) -> bool: return self._done
    def next_screen(self) -> Optional[str]: return self._next
    def finish(self, next_screen: Optional[str] = None):
        self._done = True
        self._next = next_screen
