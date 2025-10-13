from typing import List, Tuple

class ScoringRule:
    """Base class for a scoring rule.

    Each rule may contribute some dice to a score. For determining a 'single combo' lock, we expose
    a combo_size attribute representing the atomic size of this rule's fundamental scoring unit.
    Example:
        - SingleValue: combo_size = 1 (one die is atomic; multiple singles are multiple combos).
        - ThreeOfAKind: combo_size = 3
        - Straight6: combo_size = 6

    New: rule_key property (string) uniquely identifying category for selective modifiers.
    Subclasses should override _build_rule_key for specialized identification.
    """
    combo_size: int = 0  # override in subclasses

    def _build_rule_key(self) -> str:
        return self.__class__.__name__

    @property
    def rule_key(self) -> str:
        return self._build_rule_key()

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        """Return (score, indices_of_contributing_dice)."""
        raise NotImplementedError


class SingleValue(ScoringRule):
    def __init__(self, value: int, points: int):
        self.value = value
        self.points = points
        self.combo_size = 1

    def _build_rule_key(self) -> str:  # e.g., SingleValue:5
        return f"SingleValue:{self.value}"

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        indices = [i for i, d in enumerate(dice) if d == self.value]
        score = len(indices) * self.points
        return score, indices


class ThreeOfAKind(ScoringRule):
    def __init__(self, value: int, points: int):
        self.value = value
        self.points = points
        self.combo_size = 3

    def _build_rule_key(self) -> str:
        return f"ThreeOfAKind:{self.value}"

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        indices = [i for i, d in enumerate(dice) if d == self.value]
        if len(indices) >= 3:
            score = self.points
            return score, indices[:3]
        return 0, []


class Straight6(ScoringRule):
    def __init__(self, points: int):
        self.points = points
        self.combo_size = 6

    def _build_rule_key(self) -> str:
        return "Straight6"

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

    def evaluate(self, dice: List[int]) -> Tuple[int, List[int], List[Tuple[str, int]]]:
        """Return (total_score, used_indices, breakdown)

        breakdown: list of (rule_key, raw_points) for each contributing rule application.
        (Currently each rule fires at most once; if future stacking occurs, duplicates may appear.)
        """
        total_score = 0
        used_indices = set()
        breakdown: List[Tuple[str, int]] = []
        for rule in self.rules:
            score, indices = rule.match(dice)
            indices = [i for i in indices if i not in used_indices]
            if score > 0 and indices:
                total_score += score
                used_indices.update(indices)
                breakdown.append((rule.rule_key, score))
        return total_score, list(used_indices), breakdown

    def evaluate_matches(self, dice: List[int]) -> List[Tuple[ScoringRule, int, List[int]]]:
        """Return granular matches without aggregating indices; each rule attempted independently.
        Indices are raw from the rule.match (no de-dup filtering)."""
        matches: List[Tuple[ScoringRule, int, List[int]]] = []
        for rule in self.rules:
            score, indices = rule.match(dice)
            if score > 0 and indices:
                matches.append((rule, score, indices))
        return matches
