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


class FourOfAKind(ScoringRule):
    """Four of a kind: double the value of the corresponding three of a kind."""
    def __init__(self, value: int, three_kind_points: int):
        self.value = value
        self.three_kind_points = three_kind_points
        self.combo_size = 4

    def _build_rule_key(self) -> str:
        return f"FourOfAKind:{self.value}"

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        indices = [i for i, d in enumerate(dice) if d == self.value]
        if len(indices) >= 4:
            return self.three_kind_points * 2, indices[:4]
        return 0, []


class FiveOfAKind(ScoringRule):
    """Five of a kind: triple the value of the corresponding three of a kind."""
    def __init__(self, value: int, three_kind_points: int):
        self.value = value
        self.three_kind_points = three_kind_points
        self.combo_size = 5

    def _build_rule_key(self) -> str:
        return f"FiveOfAKind:{self.value}"

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        indices = [i for i, d in enumerate(dice) if d == self.value]
        if len(indices) >= 5:
            return self.three_kind_points * 3, indices[:5]
        return 0, []


class SixOfAKind(ScoringRule):
    """Six of a kind: quadruple the value of the corresponding three of a kind."""
    def __init__(self, value: int, three_kind_points: int):
        self.value = value
        self.three_kind_points = three_kind_points
        self.combo_size = 6

    def _build_rule_key(self) -> str:
        return f"SixOfAKind:{self.value}"

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        indices = [i for i, d in enumerate(dice) if d == self.value]
        if len(indices) >= 6:
            return self.three_kind_points * 4, indices[:6]
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


class Straight1to5(ScoringRule):
    def __init__(self, points: int):
        self.points = points
        self.combo_size = 5

    def _build_rule_key(self) -> str:
        return "Straight1to5"

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        if sorted(dice) == [1,2,3,4,5]:
            return self.points, list(range(5))
        return 0, []


class Straight2to6(ScoringRule):
    def __init__(self, points: int):
        self.points = points
        self.combo_size = 5

    def _build_rule_key(self) -> str:
        return "Straight2to6"

    def match(self, dice: List[int]) -> Tuple[int, List[int]]:
        if sorted(dice) == [2,3,4,5,6]:
            return self.points, list(range(5))
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
        # Process rules ordered by descending combo size so larger combos claim dice first
        ordered = sorted(self.rules, key=lambda r: getattr(r, 'combo_size', 0), reverse=True)
        for rule in ordered:
            score, indices = rule.match(dice)
            if score <= 0 or not indices:
                continue
            # Filter out already used dice
            filtered = [i for i in indices if i not in used_indices]
            # Must have full combo coverage (prevents partial overlaps from stacking).
            # For single-value rules (combo_size==1) allow any remaining single indices.
            if rule.combo_size > 1 and len(filtered) != rule.combo_size:
                continue
            # If after filtering no indices remain, skip (prevents single scoring same die twice)
            if not filtered:
                continue
            total_score += score
            used_indices.update(filtered)
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

    def selection_is_single_combo(self, dice: List[int]) -> bool:
        if not dice:
            return False
        matches = self.evaluate_matches(dice)
        if not matches:
            return False
        full_cover = [m for m in matches if len(m[2]) == len(dice)]
        if not full_cover:
            return False
        max_size = max(m[0].combo_size for m in full_cover if hasattr(m[0], "combo_size"))
        best = [m for m in full_cover if getattr(m[0], "combo_size", 0) == max_size]
        return len(best) == 1 and best[0][0].combo_size == len(dice)

    def selection_rule_key(self, dice: List[int]) -> str | None:
        if not dice:
            return None
        matches = self.evaluate_matches(dice)
        if not matches:
            return None
        full_cover = [m for m in matches if len(m[2]) == len(dice)]
        if not full_cover:
            return None
        max_size = max(m[0].combo_size for m in full_cover if hasattr(m[0], "combo_size"))
        best = [m for m in full_cover if getattr(m[0], "combo_size", 0) == max_size]
        if len(best) == 1 and best[0][0].combo_size == len(dice):
            rule = best[0][0]
            return getattr(rule, 'rule_key', rule.__class__.__name__)
        return None


def create_default_rules() -> 'ScoringRules':
    """Factory function to create a ScoringRules instance with standard Farkle rules.
    
    Returns:
        ScoringRules instance populated with all standard scoring patterns.
    """
    rules = ScoringRules()
    
    # Base three-of-a-kind values
    three_kind_values = {
        1: 1000,
        2: 200,
        3: 300,
        4: 400,
        5: 500,
        6: 600,
    }
    for v, pts in three_kind_values.items():
        rules.add_rule(ThreeOfAKind(v, pts))
        rules.add_rule(FourOfAKind(v, pts))   # double three-kind value
        rules.add_rule(FiveOfAKind(v, pts))   # triple three-kind value
        rules.add_rule(SixOfAKind(v, pts))    # quadruple three-kind value
    
    rules.add_rule(SingleValue(1, 100))
    rules.add_rule(SingleValue(5, 50))
    rules.add_rule(Straight6(1500))
    # New 5-length partial straights
    rules.add_rule(Straight1to5(1000))
    rules.add_rule(Straight2to6(1000))
    
    return rules
