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

@dataclass
class ScoreMultiplier(ScoreModifier):
    mult: float = 1.0
    priority: int = 50

    def apply(self, base: int, context: ScoreContext) -> int:
        return int(base * self.mult)

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
        adjusted = base
        for m in self._mods:
            adjusted = m.apply(adjusted, context)
        return adjusted

    def effective_multiplier(self) -> float:
        mult = 1.0
        for m in self._mods:
            if isinstance(m, ScoreMultiplier):
                mult *= m.mult
        return mult

    # Convenience for legacy style updates
    def add_multiplier_delta(self, delta: float):
        for m in self._mods:
            if isinstance(m, ScoreMultiplier):
                m.mult = max(0.0, m.mult + delta)
                return
        # If no multiplier yet, append a fresh one whose base is 1.0 + delta (or delta if chain empty)
        base = 1.0 + delta if delta >= 0 else max(0.0, 1.0 + delta)
        self.add(ScoreMultiplier(mult=base))

# Future examples (placeholders)
# class FlatBonus(ScoreModifier):
#     priority = 60
#     def __init__(self, amount: int): self.amount = amount
#     def apply(self, base: int, context: ScoreContext) -> int:
#         return base + self.amount if base > 0 else 0
