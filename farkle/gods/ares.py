"""Ares - God of War and Battle

Leveling: Gains levels based on Warfare goals completed (max level 3)
- Level 1: 2 warfare goals (+20% to warfare goals)
- Level 2: 4 more warfare goals (6 total) (Sanctify ability - change goal to warfare)
- Level 3: 6 more warfare goals (12 total) (Double all warfare goal rewards)

Favor Progression:
- Level 1: +20% scoring bonus to warfare goals
- Level 2: Sanctify ability (1 use) - change a goal's category to warfare
- Level 3: Double all warfare goal rewards (gold, income, faith, blessings)
"""

from farkle.gods.category_god import CategoryGod


class Ares(CategoryGod):
    """Ares grants powers related to warfare, combat, and conquest."""
    
    def __init__(self, game=None):
        super().__init__(
            name="Ares",
            category="warfare",
            lore="God of war, battle, and martial conquest",
            game=game
        )
