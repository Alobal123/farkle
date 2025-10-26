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
    temple_income: int = 0  # Gold awarded at the start of each level
    game: Any | None = None  # runtime-injected game; typed loosely for flexibility

    def __init__(self):
        GameObject.__init__(self, name="Player")
        self.gold = 0
        self.temple_income = 30  # Starting temple income
        self.game = None  # set by Game after construction
        self.active_effects: list = []  # TemporaryEffect instances (blessings/curses)

    def add_gold(self, amount: int) -> None:
        if amount > 0:
            self.gold += amount

    def apply_effect(self, effect) -> None:
        """Apply a temporary effect (blessing/curse) to this player."""
        if effect in self.active_effects:
            return
        effect.player = self
        self.active_effects.append(effect)
        if self.game:
            # Activate will subscribe on_event automatically since effect.active was False
            effect.activate(self.game)

    def remove_effect(self, effect) -> None:
        """Remove a temporary effect from this player."""
        if effect in self.active_effects:
            self.active_effects.remove(effect)
            if self.game:
                try:
                    effect.deactivate(self.game)
                except Exception:
                    pass


    # Player might react to events later (stats tracking, etc.)
    def on_event(self, event: GameEvent) -> None:  # type: ignore[override]
        if event.type == GameEventType.LEVEL_GENERATED:
            # Award temple income at the start of each level
            if self.temple_income > 0:
                self.add_gold(self.temple_income)
                if self.game:
                    from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                    self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={
                        "amount": self.temple_income, 
                        "source": "temple_income"
                    }))
        elif event.type == GameEventType.GOAL_FULFILLED:
            goal = event.get("goal")
            if goal and hasattr(goal, 'claim_reward'):
                gold_gained, income_gained = goal.claim_reward()
                if gold_gained > 0:
                    self.add_gold(gold_gained)
                    if self.game:
                        from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                        self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={"amount": gold_gained, "goal_name": goal.name}))  # type: ignore[attr-defined]
                if income_gained > 0:
                    self.temple_income += income_gained
                    # Publish INCOME_GAINED event for UI feedback
                    if self.game:
                        from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                        self.game.event_listener.publish(GE(GET.INCOME_GAINED, payload={
                            "amount": income_gained, 
                            "goal_name": goal.name,  # type: ignore[attr-defined]
                            "new_total": self.temple_income
                        }))


    def draw(self, surface):  # type: ignore[override]
        if not self.game:
            return
        g = self.game
        hud_padding = 10
        # Player no longer directly renders HUD; PlayerHUDSprite handles display.
        pass

    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        """Reserved for future player HUD interactions (StarterEffect removed)."""
        return False
