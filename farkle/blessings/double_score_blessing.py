"""Double Score Blessing - Doubles all scores for the next turn."""

from farkle.core.temporary_effect import TemporaryEffect
from farkle.core.effect_type import EffectType
from farkle.core.game_event import GameEvent, GameEventType
from farkle.scoring.score_modifiers import CompositePartModifier, MultiplyEffect, AllPartsMatcher


class DoubleScoreBlessing(TemporaryEffect):
    """Blessing that doubles all scores for a limited number of turns.
    
    Awarded by beggars when their petitions are fulfilled.
    """
    
    def __init__(self, duration: int = 1):
        super().__init__(
            name="Divine Fortune", 
            effect_type=EffectType.BLESSING, 
            duration=duration
        )
        # Use existing CompositePartModifier with MultiplyEffect
        self.modifier = CompositePartModifier(
            matcher=AllPartsMatcher(),
            effect=MultiplyEffect(mult=2.0),
            priority=200  # Apply after other modifiers
        )
        
    def on_activate(self, game):  # type: ignore[override]
        """Apply the score doubling modifier."""
        super().on_activate(game)
        # Add modifier to the game's scoring manager modifier chain
        try:
            if hasattr(game, 'scoring_manager') and hasattr(game.scoring_manager, 'modifier_chain'):
                game.scoring_manager.modifier_chain.add(self.modifier)
        except Exception:
            pass
    
    def on_deactivate(self, game):  # type: ignore[override]
        """Remove the score doubling modifier."""
        super().on_deactivate(game)
        # Remove modifier from the game's scoring manager modifier chain
        try:
            if hasattr(game, 'scoring_manager') and hasattr(game.scoring_manager, 'modifier_chain'):
                game.scoring_manager.modifier_chain.remove(self.modifier)
        except Exception:
            pass
