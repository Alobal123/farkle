from dataclasses import dataclass, field
from farkle.core.game_object import GameObject
from farkle.scoring.score_modifiers import ScoreModifierChain, ScoreModifier
from farkle.core.game_event import GameEventType

@dataclass
class Relic(GameObject):
    """A future gameplay relic that can contribute score modifiers.

    Relics encapsulate their own modifier chain so they can be enabled/disabled
    or stacked without mutating Player internals directly. Integration strategy:
    * Game (or Player) can aggregate chains: player_chain + all active relic chains
      when computing an effective score.
    * For now this class is inert; wiring will occur once relic acquisition exists.
    """
    active: bool = True
    modifier_chain: ScoreModifierChain = field(default_factory=ScoreModifierChain)

    def __init__(self, name: str, base_multiplier: float | None = None):
        GameObject.__init__(self, name=name)
        self.active = True
        self.modifier_chain = ScoreModifierChain()
        # Global multipliers removed; base_multiplier ignored for gameplay (kept for compat)

    def add_modifier(self, modifier: ScoreModifier):
        self.modifier_chain.add(modifier)

    def on_event(self, event):  # type: ignore[override]
        # Apply selective (non-global) modifiers during SCORE_PRE_MODIFIERS
        if event.type == GameEventType.SCORE_PRE_MODIFIERS:
            score_obj = event.get('score_obj')
            if not score_obj:
                return
            context = type('TmpCtx',(object,),{})()
            setattr(context, 'score_obj', score_obj)
            # Fold non-global modifiers modifying parts (adjusted values written in parts)
            for m in self.modifier_chain.snapshot():
                try:
                    # base passed is ignored by CompositePartModifier except for arithmetic
                    _ = m.apply(score_obj.total_effective, context)  # type: ignore[arg-type]
                except Exception:
                    pass
        return

    def draw(self, surface):  # type: ignore[override]
        # Deprecated placeholder; relics have no standalone sprite.
        return
