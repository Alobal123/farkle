from __future__ import annotations
from abc import ABC, abstractmethod
import pygame
from game_event import GameEvent

class GameObject(ABC):
    _id_seq = 0

    def __init__(self, name: str):
        GameObject._id_seq += 1
        self.id: int = GameObject._id_seq
        self.name = name

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Draw object on given surface. Objects not needing drawing can no-op."""
        raise NotImplementedError

    def on_event(self, event: GameEvent) -> None:  # default no-op
        pass

    # Convenience for filtering
    def is_type(self, cls) -> bool:
        return isinstance(self, cls)

    # Click handling (return True if consumed); standardized signature expects game + pos
    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        return False
