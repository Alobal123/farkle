from __future__ import annotations
from abc import ABC, abstractmethod
import pygame
from farkle.core.game_event import GameEvent

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
    # Activation flag. Subclasses wanting deferred activation (e.g., relic before purchase)
    # can set this False then call activate(game) later.
        self.active: bool = True
        # Internal subscription bookkeeping so deactivate can unsubscribe only
        # the callbacks this object registered through activate(). Each entry
        # is (callback, events_or_None)
        self._subscriptions: list[tuple] = []  # type: ignore[attr-defined]

    # ---------------------------------------------------------------------
    # Overridable section: subclasses typically implement one or more of:
    #   on_activate(game)   -> side-effects when first activated
    #   on_event(event)     -> react to GameEvent stream
    #   on_deactivate(game) -> cleanup / side-effects on deactivation
    # draw() is separately abstract for visual objects.
    # ---------------------------------------------------------------------

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Draw object on given surface. Objects not needing drawing can no-op."""
        raise NotImplementedError

    def on_event(self, event: GameEvent) -> None:  # default no-op
        pass

    # --- Overridable lifecycle hooks (implement in subclasses as needed) ---
    def on_activate(self, game) -> None:  # default no-op
        """Called exactly once when this object transitions from inactive to active via activate()."""
        pass

    def on_deactivate(self, game) -> None:  # default no-op
        """Called exactly once when this object transitions from active to inactive via deactivate()."""
        pass

    # --- Lifecycle helpers -------------------------------------------------
    def activate(self, game, *, events=None, callback=None) -> None:
        """Activate this object if not already active.

        Behavior:
          * Marks self.active = True
          * Subscribes self.on_event to the global event listener (optionally
            filtered to 'events') if not already subscribed via activate.
          * Optional 'callback' allows registering an additional callable
            tied to this activation (will be auto-unsubscribed on deactivate).

    Duplicate subscriptions are avoided by EventListener.
        """
        if self.active:
            # Already active: still allow adding supplemental callback
            if callback:
                game.event_listener.subscribe(callback, events)
                self._subscriptions.append((callback, events))
            return
        self.active = True
        game.event_listener.subscribe(self.on_event, events)
        self._subscriptions.append((self.on_event, events))
        if callback:
            game.event_listener.subscribe(callback, events)
            self._subscriptions.append((callback, events))
        try:
            self.on_activate(game)
        except Exception:
            pass

    def deactivate(self, game) -> None:
        """Deactivate this object, unsubscribing callbacks registered via activate()."""
        if not self.active:
            return
        self.active = False
        try:
            for cb, _events in list(self._subscriptions):
                game.event_listener.unsubscribe(cb)
        finally:
            self._subscriptions.clear()
        try:
            self.on_deactivate(game)
        except Exception:
            pass

    def emit(self, game, event_type, payload=None):
        """Convenience helper for emitting an event from this object.

        Shorthand for game.event_listener.publish(GameEvent(type, source=self, payload=payload)).
        Returns the created GameEvent for optional chaining/testing.
        """
        ev = GameEvent(event_type, source=self, payload=payload)
        try:
            game.event_listener.publish(ev)
        except Exception:
            pass
        return ev

    # Convenience for filtering
    def is_type(self, cls) -> bool:
        return isinstance(self, cls)

    # Click handling (return True if consumed); standardized signature expects game + pos
    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        return False

    def should_draw(self, game) -> bool:
        """Visibility decision for non-sprite objects (tests / legacy helpers)."""
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
