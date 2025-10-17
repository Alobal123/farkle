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
        # If None -> always visible. Else set of GameState values in which to draw.
        self.visible_states = None  # type: ignore[attr-defined]
        # Optional predicate for dynamic gating (lambda game: bool)
        self.visible_predicate = None  # type: ignore[attr-defined]
        # Interaction gating separate from visibility (object may be visible but not clickable)
        self.interactable_states = None  # type: ignore[attr-defined]
        self.interactable_predicate = None  # type: ignore[attr-defined]

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

    def should_draw(self, game) -> bool:
        """(Legacy) Visibility decision for non-sprite objects.

        New code should rely on sprite-level gating (BaseSprite.visible_states / visible_predicate).
        This method is retained only for tests injecting Dummy objects without sprites.
        """
        try:
            st = game.state_manager.get_state()
            if self.visible_states is not None and st not in self.visible_states:
                return False
            if self.visible_predicate and not self.visible_predicate(game):
                return False
            return True
        except Exception:
            return True

    def should_interact(self, game) -> bool:
        """Unified interaction decision.

        Object may be visible but not interactable. Defaults to True if no constraints.
        """
        try:
            st = game.state_manager.get_state()
            if self.interactable_states is not None and st not in self.interactable_states:
                return False
            if self.interactable_predicate and not self.interactable_predicate(game):
                return False
            return True
        except Exception:
            return True
