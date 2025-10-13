from dataclasses import dataclass, field
from game_object import GameObject
from game_event import GameEvent, GameEventType
from score_modifiers import ScoreModifier, ScoreMultiplier, ScoreModifierChain
from dataclasses import dataclass as _dc

@_dc
class _ScoreApplyContext:
    pending_raw: int

@dataclass
class Player(GameObject):
    gold: int = 0
    game: object | None = None
    modifier_chain: ScoreModifierChain = field(default_factory=ScoreModifierChain)

    def __init__(self):
        GameObject.__init__(self, name="Player")
        self.gold = 0
        self.game = None  # set by Game after construction
        # Start with a single ScoreMultiplier replicating previous behavior
        self.modifier_chain = ScoreModifierChain([ScoreMultiplier(mult=1.0)])

    def add_gold(self, amount: int) -> None:
        if amount > 0:
            self.gold += amount

    # Ability interface
    def get_score_multiplier(self) -> float:
        # Compatibility: derive effective multiplier by multiplying all multiplier-type modifiers
        total = 1.0
        for m in self.modifier_chain:
            if isinstance(m, ScoreMultiplier):
                total *= m.mult
        return total

    def add_score_multiplier(self, delta: float):
        # Adjust first ScoreMultiplier; if not present, append one
        self.modifier_chain.add_multiplier_delta(delta)

    def add_modifier(self, modifier: ScoreModifier):
        self.modifier_chain.add(modifier)

    # Player might react to events later (stats tracking, etc.)
    def on_event(self, event: GameEvent) -> None:  # type: ignore[override]
        if event.type == GameEventType.GOAL_FULFILLED:
            goal = event.get("goal")
            if goal and hasattr(goal, 'claim_reward'):
                gained = goal.claim_reward()
                if gained:
                    self.add_gold(gained)
                    # Emit GOLD_GAINED event
                    if self.game:
                        from game_event import GameEvent as GE, GameEventType as GET
                        self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={"amount": gained, "goal_name": goal.name}))  # type: ignore[attr-defined]
        elif event.type == GameEventType.GOLD_GAINED:
            # Placeholder for future tracking (e.g., achievements)
            pass
        elif event.type == GameEventType.LEVEL_ADVANCE_FINISHED:
            # Progression rule: each completed level grants +0.05 multiplier after first
            # (Mirrors previous Level.advance logic without storing on Level).
            level_index = event.get("level_index", 1)
            if level_index > 1:
                self.add_score_multiplier(0.05)
        elif event.type == GameEventType.SCORE_APPLY_REQUEST:
            goal = event.get("goal")
            pending_raw = int(event.get("pending_raw", 0) or 0)
            score_dict = event.get("score")
            if goal is not None and pending_raw > 0 and self.game:
                # Prepare context with pending raw only; modifiers inspect context.score_obj if present
                context = _ScoreApplyContext(pending_raw=pending_raw)
                # Aggregate player + relic modifiers if relic manager present
                aggregated_mods = []
                relic_manager = getattr(self.game, 'relic_manager', None)
                if relic_manager is not None:
                    try:
                        aggregated_mods = relic_manager.aggregate_modifier_chain()  # type: ignore[attr-defined]
                    except Exception:
                        aggregated_mods = list(self.modifier_chain.snapshot())
                if not aggregated_mods:
                    aggregated_mods = list(self.modifier_chain.snapshot())
                # Reconstruct score object early so modifiers can use it
                score_obj = None
                if score_dict:
                    try:
                        from score_types import Score, ScorePart
                        detailed = score_dict.get('detailed_parts') or score_dict.get('parts', [])
                        parts = [ScorePart(rule_key=pd['rule_key'], raw=pd['raw'], adjusted=pd.get('adjusted')) for pd in detailed]
                        score_obj = Score(parts=parts)
                        setattr(context, 'score_obj', score_obj)
                    except Exception:
                        score_obj = None
                adjusted = pending_raw
                for m in aggregated_mods:
                    adjusted = m.apply(adjusted, context)  # type: ignore[arg-type]
                # After modifiers, finalize score serialization
                score_out_dict = None
                if score_obj is not None:
                    try:
                        score_obj.final_global_adjusted = adjusted
                        score_out_dict = score_obj.to_dict()
                    except Exception:
                        score_out_dict = None
                from game_event import GameEvent as GE, GameEventType as GET
                payload = {"goal": goal, "pending_raw": pending_raw, "multiplier": self.get_score_multiplier(), "adjusted": adjusted}
                if score_out_dict is not None:
                    payload["score"] = score_out_dict
                self.game.event_listener.publish(GE(GET.SCORE_APPLIED, payload=payload))  # type: ignore[attr-defined]

    def draw(self, surface):  # type: ignore[override]
        # Player itself has no direct sprite; rendering handled elsewhere.
        return
