"""Hermes - God of Commerce and Trade

Leveling: Gains levels based on Commerce goals completed (max level 3)
- Level 1: 2 commerce goals (+20% to commerce goals)
- Level 2: 4 more commerce goals (6 total) (Sanctify ability - change goal to commerce)
- Level 3: 6 more commerce goals (12 total) (Double all commerce goal rewards)

Favor Progression:
- Level 1: +20% scoring bonus to commerce goals
- Level 2: Sanctify ability (1 use) - change a goal's category to commerce
- Level 3: Double all commerce goal rewards (gold, income, faith, blessings)
"""

from farkle.gods.category_god import CategoryGod


class Hermes(CategoryGod):
    """Hermes grants powers related to commerce, trade, and travel."""
    
    def __init__(self, game=None):
        super().__init__(
            name="Hermes",
            category="commerce",
            lore="God of commerce, trade, and swift travel",
            game=game
        )
