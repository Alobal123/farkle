from dataclasses import dataclass, field
from game_object import GameObject
from game_event import GameEvent, GameEventType
from score_modifiers import ScoreModifier, ScoreModifierChain
from dataclasses import dataclass as _dc
import pygame
from typing import Any
from settings import WIDTH

@_dc
class _ScoreApplyContext:
    pending_raw: int

@dataclass
class Player(GameObject):
    gold: int = 0
    game: Any | None = None  # runtime-injected game; typed loosely for flexibility
    modifier_chain: ScoreModifierChain = field(default_factory=ScoreModifierChain)

    def __init__(self):
        GameObject.__init__(self, name="Player")
        self.gold = 0
        self.game = None  # set by Game after construction
        # Initialize empty modifier chain (selective effects only)
        self.modifier_chain = ScoreModifierChain()

    def add_gold(self, amount: int) -> None:
        if amount > 0:
            self.gold += amount

    # Ability interface (global multiplier removed)

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
                    if self.game:
                        from game_event import GameEvent as GE, GameEventType as GET
                        self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={"amount": gained, "goal_name": goal.name}))  # type: ignore[attr-defined]
        elif event.type == GameEventType.GOLD_GAINED:
            pass
        elif event.type == GameEventType.LEVEL_ADVANCE_FINISHED:
            # No global multiplier progression
            pass
        elif event.type == GameEventType.SCORE_APPLY_REQUEST:
            goal = event.get("goal")
            pending_raw = int(event.get("pending_raw", 0) or 0)
            score_dict = event.get("score")
            if goal is None or pending_raw <= 0 or not self.game:
                return
            # Reconstruct score object
            score_obj = None
            if score_dict:
                try:
                    from score_types import Score, ScorePart
                    detailed = score_dict.get('detailed_parts') or score_dict.get('parts', [])
                    parts = [ScorePart(rule_key=pd['rule_key'], raw=pd['raw'], adjusted=pd.get('adjusted')) for pd in detailed]
                    score_obj = Score(parts=parts)
                except Exception:
                    score_obj = None
            if score_obj is not None:
                try:
                    from game_event import GameEvent as GE, GameEventType as GET
                    self.game.event_listener.publish_immediate(GE(GET.SCORE_PRE_MODIFIERS, payload={
                        "goal": goal,
                        "pending_raw": pending_raw,
                        "score_obj": score_obj,
                    }))
                    pending_raw = score_obj.total_effective
                except Exception:
                    pass
            # No global multipliers: adjusted equals selective effective total
            total_mult = 1.0
            adjusted = int(pending_raw)
            score_out_dict = None
            if score_obj is not None:
                try:
                    score_obj.final_global_adjusted = adjusted
                    score_out_dict = score_obj.to_dict()
                except Exception:
                    score_out_dict = None
            from game_event import GameEvent as GE, GameEventType as GET
            payload = {"goal": goal, "pending_raw": pending_raw, "multiplier": total_mult, "adjusted": adjusted}
            if score_out_dict is not None:
                payload["score"] = score_out_dict
            self.game.event_listener.publish(GE(GET.SCORE_APPLIED, payload=payload))  # type: ignore[attr-defined]

    def draw(self, surface):  # type: ignore[override]
        if not self.game:
            return
        g = self.game
        hud_padding = 10
        # Minimal HUD (global multiplier removed from gameplay)
        hud_lines = [
            f"Turns: {g.level_state.turns_left}",
            f"Gold: {self.gold}",
        ]
        line_surfs = [g.small_font.render(t, True, (250,250,250)) for t in hud_lines]
        width_needed = max(s.get_width() for s in line_surfs) + hud_padding * 2
        height_needed = sum(s.get_height() for s in line_surfs) + hud_padding * 2 + 6
        hud_rect = pygame.Rect(WIDTH - width_needed - 20, 20, width_needed, height_needed)
        pygame.draw.rect(surface, (40, 55, 70), hud_rect, border_radius=8)
        pygame.draw.rect(surface, (90, 140, 180), hud_rect, width=2, border_radius=8)
        y = hud_rect.y + hud_padding
        for s in line_surfs:
            surface.blit(s, (hud_rect.x + hud_padding, y))
            y += s.get_height() + 2
