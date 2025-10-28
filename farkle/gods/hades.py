"""Hades - God of the Underworld

Leveling: Gains levels based on Spirit goals completed (max level 3)
- Level 1: 2 spirit goals (+20% to spirit goals)
- Level 2: 4 more spirit goals (6 total) (Sanctify ability - change goal to spirit)
- Level 3: 6 more spirit goals (12 total) (Double all spirit goal rewards)

Favor Progression:
- Level 1: +20% scoring bonus to spirit goals
- Level 2: Sanctify ability (1 use) - change a goal's category to spirit
- Level 3: Double all spirit goal rewards (gold, income, faith, blessings)
"""

from farkle.gods.category_god import CategoryGod


class Hades(CategoryGod):
    """Hades grants powers related to the underworld, death, and spirits."""
    
    def __init__(self, game=None):
        super().__init__(
            name="Hades",
            category="spirit",
            lore="God of the underworld, death, and spirits",
            game=game
        )
