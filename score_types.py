from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ScorePart:
    """Simplified representation of a rule's contribution for the turn.

    Exactly one aggregated part per rule_key (multiple locks accumulate raw).
    """
    rule_key: str
    raw: int
    adjusted: int | None = None

    def effective(self) -> int:
        return self.adjusted if self.adjusted is not None else self.raw

@dataclass
class Score:
    """Composite score built from multiple ScorePart entries.

    total_raw is derived as sum(part.raw). total_effective is sum(part.effective()).
    A final_global_adjusted may store result after global multiplier chain.
    """
    parts: List[ScorePart] = field(default_factory=list)
    final_global_adjusted: Optional[int] = None  # result after global modifiers

    # Legacy from_breakdown removed (distinct parts now created incrementally).

    def add_part(self, part: ScorePart) -> None:
        self.parts.append(part)

    @property
    def total_raw(self) -> int:
        return sum(p.raw for p in self.parts)

    @property
    def total_effective(self) -> int:
        return sum(p.effective() for p in self.parts)

    def to_dict(self) -> dict:
        # Aggregate externally by rule_key to preserve earlier contract (single part per rule_key)
        aggregate: dict[str, ScorePart] = {}
        for p in self.parts:
            existing = aggregate.get(p.rule_key)
            if existing is None:
                aggregate[p.rule_key] = ScorePart(rule_key=p.rule_key, raw=p.raw, adjusted=p.adjusted)
            else:
                existing.raw += p.raw
                if existing.adjusted is not None or p.adjusted is not None:
                    existing.adjusted = (existing.adjusted or 0) + (p.adjusted if p.adjusted is not None else p.raw)
        return {
            'parts': [
                {
                    'rule_key': ap.rule_key,
                    'raw': ap.raw,
                    'adjusted': ap.adjusted,
                } for ap in aggregate.values()
            ],
            'detailed_parts': [
                {
                    'rule_key': p.rule_key,
                    'raw': p.raw,
                    'adjusted': p.adjusted,
                } for p in self.parts
            ],
            'total_raw': self.total_raw,
            'total_effective': self.total_effective,
            'final_global_adjusted': self.final_global_adjusted,
        }

    def part_by_rule(self, rule_key: str) -> Optional[ScorePart]:
        for p in self.parts:
            if p.rule_key == rule_key:
                return p
        return None

    def ensure_part(self, rule_key: str, raw: int) -> ScorePart:
        p = ScorePart(rule_key=rule_key, raw=raw)
        self.parts.append(p)
        return p

    def clone(self) -> 'Score':
        return Score(parts=[ScorePart(rule_key=p.rule_key, raw=p.raw, adjusted=p.adjusted) for p in self.parts], final_global_adjusted=self.final_global_adjusted)
