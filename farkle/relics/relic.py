from dataclasses import dataclass, field
from farkle.core.game_object import GameObject
from farkle.scoring.score_modifiers import ScoreModifierChain, ScoreModifier
from farkle.core.game_event import GameEventType

@dataclass
class Relic(GameObject):
    """Gameplay relic providing selective score modifiers.

    Each relic owns a modifier chain (part-level adjustments). Relics are
    normal GameObjects: activate() wires event subscription and emits
    SCORE_MODIFIER_ADDED events; centralized scoring applies modifiers.
    """
    active: bool = True
    modifier_chain: ScoreModifierChain = field(default_factory=ScoreModifierChain)
    # Ability modifications: list of (ability_id, delta) for UI description (non-authoritative; activation events drive logic)
    ability_mods: list[tuple[str,int]] = field(default_factory=list)

    def __init__(self, name: str):
        GameObject.__init__(self, name=name)
        self.modifier_chain = ScoreModifierChain()
        self.ability_mods = []

    def add_modifier(self, modifier: ScoreModifier):
        self.modifier_chain.add(modifier)

    # --- Internal helpers -------------------------------------------------
    def _collect_modifier_data(self, mod: ScoreModifier) -> dict:
        return {k: getattr(mod, k) for k in dir(mod)
                if not k.startswith('_') and isinstance(getattr(mod, k), (int, float, str))}

    def _emit_all_modifier_events(self, game, event_type: GameEventType):
        """Emit an event per modifier (added or removed)."""
        try:
            from farkle.core.game_event import GameEvent
            for mod in self.modifier_chain.snapshot():
                try:
                    game.event_listener.publish_immediate(GameEvent(event_type, payload={
                        "relic": self.name,
                        "modifier_type": mod.__class__.__name__,
                        "priority": getattr(mod, 'priority', None),
                        "data": self._collect_modifier_data(mod),
                    }))
                except Exception:
                    pass
        except Exception:
            pass

    def on_activate(self, game):  # type: ignore[override]
        """Base activation: emit SCORE_MODIFIER_ADDED events for all modifiers."""
        self._emit_all_modifier_events(game, GameEventType.SCORE_MODIFIER_ADDED)

    def on_deactivate(self, game):  # type: ignore[override]
        """Base deactivation: emit SCORE_MODIFIER_REMOVED for all modifiers."""
        self._emit_all_modifier_events(game, GameEventType.SCORE_MODIFIER_REMOVED)

    def on_event(self, event):  # type: ignore[override]
        # No per-event score mutation; effects applied centrally.
        return

    def draw(self, surface):  # type: ignore[override]
        return  # Relics currently have no standalone sprite.


class ExtraRerollRelic(Relic):
    """Relic that grants +1 charge to the reroll ability on activation.

    Contract: emits ABILITY_CHARGES_ADDED with payload {ability_id: 'reroll', delta: 1, source: relic_name}.
    Future abilities can listen for same event by ID.
    """
    def __init__(self):
        super().__init__(name="Token of Second Chance")
        self.ability_mods = [("reroll", 1)]

    def on_activate(self, game):  # type: ignore[override]
        # Emit ability-specific effect then defer to base for modifier events
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_CHARGES_ADDED, payload={
                "ability_id": "reroll",
                "delta": 1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_activate(game)

    def on_deactivate(self, game):  # type: ignore[override]
        """Remove the granted reroll charge while ensuring charges_per_level doesn't drop below charges_used."""
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_CHARGES_ADDED, payload={
                "ability_id": "reroll",
                "delta": -1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_deactivate(game)

class MultiRerollRelic(Relic):
    """Relic that increases reroll ability target cap by +1 (allowing two dice to be rerolled together)."""
    def __init__(self):
        super().__init__(name="Sigil of Duplication")
        self.ability_mods = [("reroll", 1)]  # descriptive only (targets, not charges)

    def on_activate(self, game):  # type: ignore[override]
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_TARGETS_ADDED, payload={
                "ability_id": "reroll",
                "delta": 1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_activate(game)

    def on_deactivate(self, game):  # type: ignore[override]
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_TARGETS_ADDED, payload={
                "ability_id": "reroll",
                "delta": -1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_deactivate(game)
