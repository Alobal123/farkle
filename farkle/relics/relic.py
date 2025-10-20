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

    def on_activate(self, game):  # type: ignore[override]
        """Emit SCORE_MODIFIER_ADDED for each score modifier this relic contributes.

        This bridges the refactored scoring flow: ScoringManager now builds its
        modifier aggregation incrementally from SCORE_MODIFIER_ADDED events
        rather than scanning active relics on RELIC_PURCHASED.
        """
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            for mod in self.modifier_chain.snapshot():
                try:
                    # Collect simple public scalar attributes (int/float/str) for reconstruction.
                    data = {k: getattr(mod, k) for k in dir(mod)
                            if not k.startswith('_') and isinstance(getattr(mod, k), (int, float, str))}
                    game.event_listener.publish_immediate(GameEvent(GameEventType.SCORE_MODIFIER_ADDED, payload={
                        "relic": self.name,
                        "modifier_type": mod.__class__.__name__,
                        "priority": getattr(mod, 'priority', None),
                        "data": data,
                    }))
                except Exception:
                    pass
        except Exception:
            pass

    def on_deactivate(self, game):  # type: ignore[override]
        """Emit SCORE_MODIFIER_REMOVED for each modifier this relic contributed.

        Ensures ScoringManager prunes stale modifiers if a relic is disabled.
        """
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            for mod in self.modifier_chain.snapshot():
                try:
                    data = {k: getattr(mod, k) for k in dir(mod)
                            if not k.startswith('_') and isinstance(getattr(mod, k), (int, float, str))}
                    game.event_listener.publish_immediate(GameEvent(GameEventType.SCORE_MODIFIER_REMOVED, payload={
                        "relic": self.name,
                        "modifier_type": mod.__class__.__name__,
                        "priority": getattr(mod, 'priority', None),
                        "data": data,
                    }))
                except Exception:
                    pass
        except Exception:
            pass

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
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_CHARGES_ADDED, payload={
                "ability_id": "reroll",
                "delta": 1,
                "source": self.name
            }))
            # Emit score modifier events for each modifier this relic contributes
            for mod in self.modifier_chain.snapshot():
                try:
                    game.event_listener.publish_immediate(GameEvent(GameEventType.SCORE_MODIFIER_ADDED, payload={
                        "relic": self.name,
                        "modifier_type": mod.__class__.__name__,
                        "priority": getattr(mod, 'priority', None),
                        "data": {k: getattr(mod, k) for k in dir(mod) if not k.startswith('_') and isinstance(getattr(mod, k), (int,float,str))}
                    }))
                except Exception:
                    pass
        except Exception:
            pass

    def on_deactivate(self, game):  # type: ignore[override]
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            # Emit removal for reroll ability charge
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_CHARGES_ADDED, payload={
                "ability_id": "reroll",
                "delta": -1,
                "source": self.name
            }))
            # Emit removal events for each score modifier (in case relic gets deactivated mid-level)
            for mod in self.modifier_chain.snapshot():
                try:
                    data = {k: getattr(mod, k) for k in dir(mod)
                            if not k.startswith('_') and isinstance(getattr(mod, k), (int, float, str))}
                    game.event_listener.publish_immediate(GameEvent(GameEventType.SCORE_MODIFIER_REMOVED, payload={
                        "relic": self.name,
                        "modifier_type": mod.__class__.__name__,
                        "priority": getattr(mod, 'priority', None),
                        "data": data,
                    }))
                except Exception:
                    pass
        except Exception:
            pass
