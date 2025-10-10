from dataclasses import dataclass

@dataclass
class Player:
    """Player meta progression stats.

    For now only gold coins; extend later with relics, achievements, etc.
    """
    gold: int = 0

    def add_gold(self, amount: int) -> None:
        if amount > 0:
            self.gold += amount
