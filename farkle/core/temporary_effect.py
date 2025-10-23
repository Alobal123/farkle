from __future__ import annotations
from dataclasses import dataclass
from farkle.core.game_object import GameObject
from farkle.core.effect_type import EffectType
from farkle.core.game_event import GameEvent, GameEventType


@dataclass
class TemporaryEffect(GameObject):
    """Base class for temporary blessings and curses affecting a player.

    Turn-end semantics:
    Duration now counts remaining completed turns. It decrements exactly once
    when a TURN_END event fires whose reason is one of:
      - 'banked'
      - 'farkle'
      - 'farkle_forfeit'
      - 'level_complete'

    It does NOT decrement on: TURN_ROLL, BANK, TURN_BANKED, GOAL_FULFILLED, or other
    intermediate events; those are intra-turn actions.
    """
    effect_type: EffectType
    duration: int  # in completed turns remaining
    
    def __init__(self, name: str, effect_type: EffectType, duration: int):
        super().__init__(name=name)
        # Effects start inactive; Player will call activate() after attaching.
        self.active = False  # override default active True from GameObject
        self.effect_type = effect_type
        self.duration = duration
        self.player = None  # set when applied to player
        # Track whether we've already decremented for the current turn segment (a "consumable roll")
        # Reset when a new turn starts or after we consume a decrement via BANK / FARKLE / GOAL_FULFILLED without a roll.
        self._decremented_this_turn = False
        
    def draw(self, surface):  # type: ignore[override]
        """Effects do not render directly (may show in player HUD)."""
        pass
    
    def on_event(self, event: GameEvent):  # type: ignore[override]
        """Respond to game events; decrement only on qualified TURN_END reasons."""
        et = event.type
        # Reset per-turn guard at start of new turn (for completeness)
        if et == GameEventType.TURN_START:
            self._decremented_this_turn = False
            return
        if et == GameEventType.TURN_END:
            reason = (event.get('reason') or '').lower()
            if reason in {"banked", "farkle", "farkle_forfeit", "level_complete"} and not self._decremented_this_turn:
                self._consume_one(force=True)

    def _consume_one(self, force: bool = False):
        # After new semantics, force flag just ensures per-turn guard engaged.
        self._decremented_this_turn = True
        self.duration -= 1
        if self.duration <= 0 and self.player and self.player.game:
            # Auto remove then deactivate
            if self in self.player.active_effects:
                try:
                    self.player.active_effects.remove(self)
                except Exception:
                    pass
            try:
                self.deactivate(self.player.game)
            except Exception:
                pass
    
    def on_activate(self, game):  # type: ignore[override]
        """Override in subclasses to apply effect logic.
        
        Effects should subscribe to events here if needed and emit activation events.
        """
        # Emit effect activation event
        try:
            game.event_listener.publish(GameEvent(
                GameEventType.MESSAGE, 
                payload={"text": f"{'Blessing' if self.effect_type == EffectType.BLESSING else 'Curse'}: {self.name} applied for {self.duration} rolls."}
            ))
        except Exception:
            pass
    
    def on_deactivate(self, game):  # type: ignore[override]
        """Override in subclasses to clean up effect logic.
        
        Effects should unsubscribe and revert changes here.
        """
        # Emit effect deactivation event
        try:
            game.event_listener.publish(GameEvent(
                GameEventType.MESSAGE,
                payload={"text": f"{self.name} has expired."}
            ))
        except Exception:
            pass


__all__ = ["TemporaryEffect"]

