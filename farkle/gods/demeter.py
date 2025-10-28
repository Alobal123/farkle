"""Demeter - Goddess of Harvest and Nature

Leveling: Gains levels based on Nature goals completed (max level 3)
- Level 1: 2 nature goals (+20% to nature goals)
- Level 2: 4 more nature goals (6 total) (Sanctify ability - change goal to nature)
- Level 3: 6 more nature goals (12 total) (Double all nature goal rewards)

Favor Progression:
- Level 1: +20% scoring bonus to nature goals
- Level 2: Sanctify ability (1 use) - change a goal category to nature
- Level 3: Double all nature goal rewards (gold, income, faith, blessings)
"""

from farkle.gods.category_god import CategoryGod


class Demeter(CategoryGod):
    """Demeter grants powers related to harvest, growth, and natural abundance."""
    
    def __init__(self, game=None):
        super().__init__(
            name="Demeter",
            category="nature",
            lore="Goddess of harvest, growth, and natural abundance",
            game=game
        )


__all__ = ["Demeter"]
