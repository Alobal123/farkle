from dataclasses import dataclass, field
from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEvent, GameEventType
from dataclasses import dataclass as _dc
import pygame
from typing import Any
from farkle.ui.settings import WIDTH


@dataclass
class Player(GameObject):
    gold: int = 0
    game: Any | None = None  # runtime-injected game; typed loosely for flexibility

    def __init__(self):
        GameObject.__init__(self, name="Player")
        self.gold = 0
        self.game = None  # set by Game after construction

    def add_gold(self, amount: int) -> None:
        if amount > 0:
            self.gold += amount


    # Player might react to events later (stats tracking, etc.)
    def on_event(self, event: GameEvent) -> None:  # type: ignore[override]
        if event.type == GameEventType.GOAL_FULFILLED:
            goal = event.get("goal")
            if goal and hasattr(goal, 'claim_reward'):
                gained = goal.claim_reward()
                if gained:
                    self.add_gold(gained)
                    if self.game:
                        from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                        self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={"amount": gained, "goal_name": goal.name}))  # type: ignore[attr-defined]


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
