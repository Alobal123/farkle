from dataclasses import dataclass, field
from game_object import GameObject
from score_modifiers import ScoreModifierChain, ScoreModifier, ScoreMultiplier

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
        if base_multiplier is not None:
            self.modifier_chain.add(ScoreMultiplier(mult=base_multiplier))

    def add_modifier(self, modifier: ScoreModifier):
        self.modifier_chain.add(modifier)

    def get_effective_multiplier(self) -> float:
        return self.modifier_chain.effective_multiplier()

    # Placeholder for event reaction if relics will respond to events
    def on_event(self, event):  # type: ignore[override]
        return

    def draw(self, surface):  # type: ignore[override]
        return
