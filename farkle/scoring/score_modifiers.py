from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Iterable, List, Sequence

class ScoreContext(Protocol):
    pending_raw: int
    # Optional goal reference for goal-conditional modifiers.
    goal: object | None

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

    def remove_by_identity(self, modifier_type: str, data: dict) -> bool:
        """Remove first modifier matching class name and provided scalar attributes.

        Returns True if removed, False otherwise.
        """
        for m in list(self._mods):
            try:
                if m.__class__.__name__ != modifier_type:
                    continue
                # All key/value pairs in data must match getattr(m, key)
                if all(getattr(m, k, None) == v for k, v in data.items()):
                    self._mods.remove(m)
                    return True
            except Exception:
                continue
        return False

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

#############################################
# Goal-conditional modifier wrappers         #
#############################################

class ConditionalScoreModifier(ScoreModifier):
    """Base wrapper that applies an inner modifier only if predicate(context) is True.

    Provides a composable way to gate any existing modifier by goal or other context attributes
    without changing its internal logic. Keeps purity and test determinism.
    """
    priority: int = 60  # run after part-level adjustments by default

    def __init__(self, inner: ScoreModifier, predicate):
        self.inner = inner
        # Inherit inner priority but run slightly after to ensure part adjustments exist
        try:
            self.priority = int(getattr(inner, 'priority', 60)) + 1
        except Exception:
            self.priority = 60
        self.predicate = predicate

    def apply(self, base: int, context: ScoreContext) -> int:  # pragma: no cover (logic simple)
        try:
            if not self.predicate(context):
                return base
            return self.inner.apply(base, context)
        except Exception:
            return base


class MandatoryGoalOnly(ConditionalScoreModifier):
    """Applies inner modifier only when context.goal is present and goal.mandatory is True."""
    def __init__(self, inner: ScoreModifier):
        super().__init__(inner, predicate=lambda ctx: getattr(getattr(ctx, 'goal', None), 'mandatory', False) is True)


class OptionalGoalOnly(ConditionalScoreModifier):
    """Applies inner modifier only when context.goal is present and goal.mandatory is False."""
    def __init__(self, inner: ScoreModifier):
        super().__init__(inner, predicate=lambda ctx: getattr(getattr(ctx, 'goal', None), 'mandatory', None) is False)


#############################################
# Global (all-parts) multiplier              #
#############################################

class GlobalPartsMultiplier(ScoreModifier):
    """Multiply every part's effective value by a factor.

    Implemented as a dedicated modifier (rather than CompositePartModifier) for efficiency.
    After application, ScoringManager will recompute total from part adjusted values.
    """
    def __init__(self, mult: float, priority: int = 58):
        self.mult = mult
        self.priority = priority

    def apply(self, base: int, context: ScoreContext) -> int:  # pragma: no cover simple math
        if self.mult == 1.0:
            return base
        score_obj = getattr(context, 'score_obj', None)
        if score_obj is None:
            # Fallback: scale the aggregated base directly
            return int(base * self.mult)
        try:
            for p in score_obj.parts:
                current = p.adjusted if p.adjusted is not None else p.raw
                new_val = int(current * self.mult)
                if new_val != current:
                    p.adjusted = new_val
        except Exception:
            return base
        # Let chain recompute total from parts later
        return base
        
