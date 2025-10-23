from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Iterable, Optional

from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEvent, GameEventType
from farkle.scoring.score_types import Score, ScorePart
from farkle.scoring.score_modifiers import ScoreModifierChain, ScoreModifier, ScoreContext

class _ScoreCtx:
    """Concrete context implementing ScoreContext protocol for modifier application."""
    def __init__(self, score_obj: Score):
        self.score_obj = score_obj
        self.pending_raw = score_obj.total_raw


@dataclass
class ScoringManager(GameObject):
    """Central scoring coordinator.

    Responsibilities:
    * Own active scoring rules (delegates to Game.rules for now; future: move rules fully here).
    * Aggregate all part-level score modifiers contributed by relics (and future sources) via SCORE_MODIFIER_ADDED events.
    * Provide preview() and finalize() helpers returning the same structure previous Game.compute_preview produced.
    * Emit SCORE_PREVIEW_REQUEST and SCORE_PREVIEW_COMPUTED events for compatibility.
    * Track per-turn cumulative score (turn_score) and current selection preview cache.
    * Incrementally builds modifier_chain on SCORE_MODIFIER_ADDED (no bulk rebuild on RELIC_PURCHASED anymore).
    """
    game: object  # runtime Game reference (no direct type import to avoid circular dependency)
    modifier_chain: ScoreModifierChain = field(default_factory=ScoreModifierChain)
    turn_score: int = 0
    current_preview: Optional[dict] = None
    modifier_records: list[dict] = field(default_factory=list)

    def __init__(self, game):
        GameObject.__init__(self, name="ScoringManager")
        self.game = game
        self.modifier_chain = ScoreModifierChain()
        self.turn_score = 0
        self.current_preview = None
        self.modifier_records = []

    # --- Event handling ----------------------------------------------------
    def on_event(self, event: GameEvent):  # type: ignore[override]
        et = event.type
        if et == GameEventType.SCORE_MODIFIER_ADDED:
            # Construct a lightweight modifier instance if possible from payload; fallback to no-op.
            payload = event.payload or {}
            relic_name = payload.get('relic')
            modifier_type = payload.get('modifier_type')
            data = payload.get('data', {})
            from farkle.scoring.score_modifiers import RuleSpecificMultiplier, FlatRuleBonus, ScoreModifier
            created: Optional[ScoreModifier] = None
            try:
                # Heuristic mapping based on known modifier class names
                if modifier_type == 'RuleSpecificMultiplier' and 'rule_key' in data and 'mult' in data:
                    created = RuleSpecificMultiplier(rule_key=data['rule_key'], mult=float(data['mult']))
                elif modifier_type == 'FlatRuleBonus' and 'rule_key' in data and 'amount' in data:
                    created = FlatRuleBonus(rule_key=data['rule_key'], amount=int(data['amount']))
            except Exception:
                created = None
            if created:
                self.modifier_chain.add(created)
                try:
                    self.modifier_records.append({
                        'type': modifier_type,
                        'data': data
                    })
                except Exception:
                    pass
        elif et == GameEventType.SCORE_MODIFIER_REMOVED:
            payload = event.payload or {}
            modifier_type = payload.get('modifier_type')
            data = payload.get('data', {}) if isinstance(payload.get('data'), dict) else {}
            try:
                self.modifier_chain.remove_by_identity(modifier_type, data)  # type: ignore[attr-defined]
                # Remove first matching record for bookkeeping
                for rec in list(self.modifier_records):
                    if rec.get('type') == modifier_type and all(rec.get('data', {}).get(k) == v for k, v in data.items()):
                        self.modifier_records.remove(rec)
                        break
            except Exception:
                pass
        elif et == GameEventType.TURN_END:
            # Clear per-turn state after bank/farkle.
            self.turn_score = 0
            self.current_preview = None
        elif et == GameEventType.LOCK:
            # Update turn_score incrementally when a lock adds points (points in payload)
            pts = int(event.get('points', 0) or 0)
            if pts > 0:
                self.turn_score += pts
        elif et == GameEventType.SCORE_APPLY_REQUEST:
            # Centralized application of pending score for a goal.
            goal = event.get('goal')
            pending_raw = int(event.get('pending_raw', 0) or 0)
            if goal is None or pending_raw <= 0:
                return
            score_dict = event.get('score')
            score_obj: Optional[Score] = None
            if score_dict:
                try:
                    detailed = score_dict.get('detailed_parts') or score_dict.get('parts', [])
                    score_obj = Score()
                    for pd in detailed:
                        rk = pd.get('rule_key')
                        raw = int(pd.get('raw', 0))
                        if rk and raw > 0:
                            score_obj.add_part(ScorePart(rule_key=rk, raw=raw))
                except Exception:
                    score_obj = None
            # Use unified computation (no preview events during apply)
            parts_for_preview: List[tuple[str,int]] = []
            if score_obj is not None:
                parts_for_preview = [(p.rule_key, p.raw) for p in score_obj.parts]
            comp = self._compute_score_dict(parts_for_preview, emit_preview_events=False, source='apply') if parts_for_preview else {
                'parts': [], 'total_raw': pending_raw, 'selective_effective': pending_raw, 'multiplier': 1.0, 'final_preview': pending_raw, 'score': None
            }
            adjusted = int(comp.get('final_preview', pending_raw))
            # Patch adjusted values back into score_obj parts
            if score_obj is not None:
                pv_parts = comp.get('parts', [])
                for p in score_obj.parts:
                    for pp in pv_parts:
                        if pp.get('rule_key') == p.rule_key:
                            p.adjusted = pp.get('adjusted')
                            break
            out_score_dict = None
            if score_obj is not None:
                try:
                    score_obj.final_global_adjusted = adjusted
                    out_score_dict = score_obj.to_dict()
                except Exception:
                    out_score_dict = None
            from farkle.core.game_event import GameEvent as GE, GameEventType as GET
            payload = {"goal": goal, "pending_raw": adjusted, "multiplier": 1.0, "adjusted": adjusted}
            if out_score_dict is not None:
                payload['score'] = out_score_dict
            try:
                el = getattr(self.game, 'event_listener', None)
                if el:
                    el.publish(GE(GET.SCORE_APPLIED, payload=payload))
            except Exception:
                pass


    # --- Preview / scoring API ---------------------------------------------
    def preview(self, parts: List[tuple[str,int]], source: str = "selection") -> dict:
        """Public preview API with event emission."""
        result = self._compute_score_dict(parts, emit_preview_events=True, source=source)
        self.current_preview = result
        return result

    # Convenience wrapper for a single rule part
    def preview_single(self, rule_key: str, raw: int, source: str = "single") -> dict:
        return self.preview([(rule_key, raw)], source=source)

    # Reset per-level (called when level resets) preserving relic state; caller decides if modifiers rebuild.
    def reset_level(self):
        self.turn_score = 0
        self.current_preview = None

    # Provide a finalize helper if future global adjustments return different value.
    def finalize(self, parts: List[tuple[str,int]], source: str = "final") -> dict:
        return self.preview(parts, source=source)

    # --- Direct dice scoring -------------------------------------------------
    def compute_from_dice(self, dice_values: List[int], source: str = "dice") -> dict:
        """Evaluate raw parts from dice using game's ScoringRules then apply modifiers."""
        parts: List[tuple[str,int]] = []
        try:
            total, used, breakdown = self._evaluate_dice(dice_values)
            # breakdown is list[(rule_key, raw_points)]
            parts = [(rk, pts) for rk, pts in breakdown]
        except Exception:
            parts = []
        if not parts:
            return {"parts": [], "total_raw": 0, "selective_effective": 0, "multiplier": 1.0, "final_preview": 0, "score": None}
        return self.preview(parts, source=source)

    # Internal dice evaluation wrapper (migration path from Game.rules direct use)
    def _evaluate_dice(self, dice_values: List[int]) -> tuple[int, list[int], list[tuple[str,int]]]:
        rules = getattr(self.game, 'rules', None)
        if rules is None:
            return 0, [], []
        try:
            return rules.evaluate(dice_values)
        except Exception:
            return 0, [], []

    # GameObject draw override (non-visual)
    def draw(self, surface):  # type: ignore[override]
        return None

    # --- Internal unified computation helper ------------------------------
    def _compute_score_dict(self, parts: List[tuple[str,int]], emit_preview_events: bool, source: str) -> dict:
        """Construct Score, apply selective modifiers, optionally emit preview events.

        Returns dict with keys: parts, total_raw, selective_effective, multiplier, final_preview, score.
        """
        score_obj = Score()
        for rk, raw in parts:
            try:
                score_obj.add_part(ScorePart(rule_key=rk, raw=int(raw)))
            except Exception:
                pass
        adjusted_total = score_obj.total_effective
        # Build a dynamic merged modifier list: events-injected chain + live active relic chains.
        try:
            context = _ScoreCtx(score_obj)
            from farkle.scoring.score_modifiers import ScoreModifierChain, ScoreModifier
            merged = ScoreModifierChain()
            # Deduplicate by (class name, scalar attribute values)
            seen: set[tuple[str, tuple]] = set()
            def _add_mod(m: ScoreModifier):
                try:
                    # Collect simple scalar identity snapshot for dedupe
                    attrs = []
                    for attr in ('rule_key','mult','amount','priority'):
                        if hasattr(m, attr):
                            attrs.append(getattr(m, attr))
                    ident = (m.__class__.__name__, tuple(attrs))
                    if ident in seen:
                        return
                    seen.add(ident)
                    merged.add(m)
                except Exception:
                    merged.add(m)
            # Event-populated modifiers
            for m in self.modifier_chain.snapshot():
                _add_mod(m)
            # Live relic modifiers (tests may append relic directly without activation events)
            try:
                relic_mgr = getattr(self.game, 'relic_manager', None)
                if relic_mgr:
                    for relic in getattr(relic_mgr, 'active_relics', []):
                        if not getattr(relic, 'active', True):
                            continue
                        for m in relic.modifier_chain.snapshot():
                            _add_mod(m)
            except Exception:
                pass
            adjusted_total = merged.apply(score_obj.total_raw, context)
        except Exception:
            adjusted_total = score_obj.total_effective
        result = {
            "parts": [{"rule_key": p.rule_key, "raw": p.raw, "adjusted": p.adjusted} for p in score_obj.parts],
            "total_raw": score_obj.total_raw,
            "selective_effective": adjusted_total,
            "multiplier": 1.0,
            "final_preview": adjusted_total,
            "score": score_obj.to_dict(),
        }
        if emit_preview_events:
            from farkle.core.game_event import GameEvent as GE, GameEventType as GET
            try:
                el = getattr(self.game, 'event_listener', None)
                if el:
                    el.publish(GE(GET.SCORE_PREVIEW_REQUEST, payload={
                        "parts": [{"rule_key": rk, "raw": raw} for rk, raw in parts],
                        "source": source
                    }))
                    el.publish(GE(GET.SCORE_PREVIEW_COMPUTED, payload=result | {"source": source}))
            except Exception:
                pass
        return result

    # --- Goal pending projection (no preview events) ---------------------
    def project_goal_pending(self, goal) -> int:
        """Return adjusted projection for a goal's current pending_raw using selective modifiers.

        Replaces legacy Game.compute_goal_pending_final. Accessed via Goal.projected_pending().
        Does NOT emit preview events (pure calculation). Falls back to raw pending if score object missing.
        """
        try:
            pending_raw = int(getattr(goal, 'pending_raw', 0) or 0)
            if pending_raw <= 0:
                return 0
            score_obj = getattr(goal, '_pending_score', None)
            if score_obj is None:
                return pending_raw
            clone = score_obj.clone()
            parts = [(p.rule_key, p.raw) for p in clone.parts]
            comp = self._compute_score_dict(parts, emit_preview_events=False, source='goal_pending')
            return int(comp.get('final_preview', pending_raw))
        except Exception:
            return int(getattr(goal, 'pending_raw', 0) or 0)
