from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Iterable, List, Sequence

class ScoreContext(Protocol):
    pending_raw: int
    # May be extended with more fields later (e.g., goal, player, level_index)

class ScoreModifier(ABC):
    """Abstract base for score modifiers.

    Implementations produce an adjusted score given a base pending_raw value and
    optionally mutate context / produce side data. They must be pure functions of
    inputs for deterministic tests (no hidden state changes besides internal counters).
    """
    priority: int = 100  # lower runs earlier

    @abstractmethod
    def apply(self, base: int, context: ScoreContext) -> int:  # pragma: no cover - interface
        """Return adjusted score (does not modify base)."""
        raise NotImplementedError


class ScoreModifierChain:
    """Encapsulates an ordered collection of ScoreModifiers.

    Responsibilities:
    * Maintain insertion & priority ordering.
    * Provide fold application over a base score with a given context.
    * Compute derived aggregate values (e.g., effective multiplier) for UI.
    * Support extension sources (Player, Relics, Temporary buffs) by allowing
      additive composition of chains or external views.
    """
    __slots__ = ("_mods",)

    def __init__(self, modifiers: Iterable[ScoreModifier] | None = None):
        self._mods: List[ScoreModifier] = list(modifiers) if modifiers else []
        self._sort()

    # --- internal helpers ---
    def _sort(self):
        self._mods.sort(key=lambda m: getattr(m, 'priority', 100))

    # --- mutation API ---
    def add(self, modifier: ScoreModifier) -> None:
        self._mods.append(modifier)
        self._sort()

    def extend(self, mods: Iterable[ScoreModifier]) -> None:
        self._mods.extend(mods)
        self._sort()

    def remove(self, modifier: ScoreModifier) -> None:
        if modifier in self._mods:
            self._mods.remove(modifier)

    # --- query API ---
    def __iter__(self):  # pragma: no cover - trivial
        return iter(self._mods)

    def snapshot(self) -> Sequence[ScoreModifier]:
        return tuple(self._mods)

    def apply(self, base: int, context: ScoreContext) -> int:
        """Apply modifiers.
        For selective part modifiers (CompositePartModifier descendants), we mutate parts and
        then recompute aggregate from part effective values.
        """
        score_obj = getattr(context, 'score_obj', None)
        running = base
        # Apply all modifiers (selective CompositePartModifier effects)
        for m in self._mods:
            running = m.apply(running, context)
        # Recompute base from parts if available (sum of effective values)
        if score_obj is not None:
            try:
                # Each part holds raw and optional adjusted value; adjusted is authoritative once set.
                # Distinct parts model => total is just sum of effective values, no need for inference heuristics.
                running = sum((p.adjusted if p.adjusted is not None else p.raw) for p in score_obj.parts)
            except Exception:
                pass
        return running

#############################################
# Matcher / Effect abstraction layer        #
#############################################

class PartMatcher(Protocol):  # pragma: no cover - interface type
    def select(self, score_obj) -> List: ...

@dataclass
class RuleKeyMatcher:
    rule_key: str
    def select(self, score_obj) -> List:
        if not score_obj:
            return []
        return [p for p in getattr(score_obj, 'parts', []) if p.rule_key == self.rule_key]


class PartEffect(Protocol):  # pragma: no cover - interface type
    def apply(self, parts: List, context: ScoreContext) -> int: ...  # returns total delta to base

@dataclass
class MultiplyEffect:
    mult: float
    def apply(self, parts, context: ScoreContext) -> int:
        if self.mult == 1.0:
            return 0
        delta_total = 0
        for part in parts:
            current = part.adjusted if part.adjusted is not None else part.raw
            new_val = int(current * self.mult)
            delta = new_val - current
            if delta != 0:
                part.adjusted = new_val
                delta_total += delta
        return delta_total

@dataclass
class FlatAddEffect:
    amount: int
    def apply(self, parts, context: ScoreContext) -> int:
        if self.amount == 0:
            return 0
        delta_total = 0
        for part in parts:
            # With distinct parts per lock, per-occurrence just means once per part.
            add_amount = self.amount
            current = part.adjusted if part.adjusted is not None else part.raw
            new_val = current + add_amount
            part.adjusted = new_val
            delta_total += add_amount
        return delta_total

@dataclass
class CompositePartModifier(ScoreModifier):
    matcher: PartMatcher
    effect: PartEffect
    priority: int = 55

    def apply(self, base: int, context: ScoreContext) -> int:
        score_obj = getattr(context, 'score_obj', None)
        if score_obj is None:
            return base
        try:
            parts = self.matcher.select(score_obj)
            if not parts:
                return base
            delta = self.effect.apply(parts, context)
            if delta:
                return base + delta
            return base
        except Exception:
            return base

#############################################
# Backwards-compatible concrete modifiers   #
#############################################

@dataclass
class RuleSpecificMultiplier(CompositePartModifier):
    rule_key: str = ""
    mult: float = 1.0
    priority: int = 55
    def __post_init__(self):
        # Rebind matcher/effect for parent logic
        object.__setattr__(self, 'matcher', RuleKeyMatcher(self.rule_key))
        object.__setattr__(self, 'effect', MultiplyEffect(self.mult))
    # Keep constructor signature (rule_key, mult)
    def __init__(self, rule_key: str, mult: float = 1.0):  # type: ignore[override]
        object.__setattr__(self, 'rule_key', rule_key)
        object.__setattr__(self, 'mult', mult)
        object.__setattr__(self, 'priority', 55)
        object.__setattr__(self, 'matcher', RuleKeyMatcher(rule_key))
        object.__setattr__(self, 'effect', MultiplyEffect(mult))


# Flat bonus applied only to a specific rule_key's parts (adds 'amount' to each matching part)
@dataclass
class FlatRuleBonus(CompositePartModifier):
    rule_key: str = ""
    amount: int = 0
    priority: int = 56
    def __post_init__(self):
        object.__setattr__(self, 'matcher', RuleKeyMatcher(self.rule_key))
        object.__setattr__(self, 'effect', FlatAddEffect(self.amount))
    def __init__(self, rule_key: str, amount: int = 0):  # type: ignore[override]
        object.__setattr__(self, 'rule_key', rule_key)
        object.__setattr__(self, 'amount', amount)
        object.__setattr__(self, 'priority', 56)
        object.__setattr__(self, 'matcher', RuleKeyMatcher(rule_key))
        object.__setattr__(self, 'effect', FlatAddEffect(amount))
        # Semantics: adds 'amount' to every matching part independently (stackable per lock instance).
        
