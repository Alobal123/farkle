from collections import Counter
from typing import List, Tuple

class ScoringRule:
    """Base class for a scoring rule."""
    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        """Return (score, indices_of_contributing_dice)."""
        raise NotImplementedError


class SingleValue(ScoringRule):
    def __init__(self, value: int, points: int):
        self.value = value
        self.points = points

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        # If there are three or more of this value, defer entirely to a ThreeOfAKind
        # (or higher) rule so we don't consume some of the dice and block the set.
        if dice.count(self.value) >= 3:
            return 0, []
        indices = [i for i, d in enumerate(dice) if d == self.value]
        score = len(indices) * self.points
        return score, indices


class ThreeOfAKind(ScoringRule):
    def __init__(self, value: int, points: int):
        self.value = value
        self.points = points

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        indices = [i for i, d in enumerate(dice) if d == self.value]
        if len(indices) >= 3:
            score = self.points
            return score, indices[:3]
        return 0, []


class Straight6(ScoringRule):
    def __init__(self, points: int):
        self.points = points

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        if sorted(dice) == [1, 2, 3, 4, 5, 6]:
            return self.points, list(range(6))
        return 0, []


class ScoringRules:
    """Container for all active scoring rules."""
    def __init__(self):
        self.rules: List[ScoringRule] = []

    def add_rule(self, rule: ScoringRule):
        self.rules.append(rule)

    def remove_rule(self, rule_type: type):
        self.rules = [r for r in self.rules if not isinstance(r, rule_type)]

    def evaluate(self, dice: List[int]) -> Tuple[int, List[int]]:
        total_score = 0
        used_indices = set()

        for rule in self.rules:
            score, indices = rule.match(dice)
            # Avoid double-counting dice already used
            indices = [i for i in indices if i not in used_indices]
            if score > 0 and indices:
                total_score += score
                used_indices.update(indices)

        return total_score, list(used_indices)
