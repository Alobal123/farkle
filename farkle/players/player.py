from dataclasses import dataclass, field
from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEvent, GameEventType
from dataclasses import dataclass as _dc
import pygame
from typing import Any, TYPE_CHECKING
from farkle.ui.settings import WIDTH

if TYPE_CHECKING:
    from farkle.game import Game


@dataclass
class Player(GameObject):
    gold: int = 0
    faith: int = 0  # Meta currency (persists across games)
    temple_income: int = 0  # Gold awarded at the start of each level

    def __init__(self, game: 'Game'):
        GameObject.__init__(self, name="Player")
        self.game = game
        self.gold = 0
        self.faith = 0
        self.temple_income = 30  # Starting temple income
        self.active_effects: list = []  # TemporaryEffect instances (blessings/curses)

    def add_gold(self, amount: int) -> None:
        if amount > 0:
            self.gold += amount

    def add_faith(self, amount: int) -> None:
        if amount > 0:
            self.faith += amount

    def apply_effect(self, effect) -> None:
        """Apply a temporary effect (blessing/curse) to this player."""
        if effect in self.active_effects:
            return
        effect.player = self
        self.active_effects.append(effect)
        # Activate will subscribe on_event automatically since effect.active was False
        effect.activate(self.game)

    def remove_effect(self, effect) -> None:
        """Remove a temporary effect from this player."""
        if effect in self.active_effects:
            self.active_effects.remove(effect)
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
                from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={
                    "amount": self.temple_income, 
                    "source": "temple_income"
                }))
        elif event.type == GameEventType.GOAL_FULFILLED:
            goal = event.get("goal")
            if goal and hasattr(goal, 'claim_reward'):
                gold_gained, income_gained, blessing_type, faith_gained = goal.claim_reward()
                if gold_gained > 0:
                    self.add_gold(gold_gained)
                    from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                    self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={"amount": gold_gained, "goal_name": goal.name}))  # type: ignore[attr-defined]
                if income_gained > 0:
                    self.temple_income += income_gained
                    # Publish INCOME_GAINED event for UI feedback
                    from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                    self.game.event_listener.publish(GE(GET.INCOME_GAINED, payload={
                        "amount": income_gained, 
                        "goal_name": goal.name,  # type: ignore[attr-defined]
                        "new_total": self.temple_income
                    }))
                if faith_gained > 0:
                    self.add_faith(faith_gained)
                    from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                    self.game.event_listener.publish(GE(GET.FAITH_GAINED, payload={
                        "amount": faith_gained,
                        "goal_name": goal.name  # type: ignore[attr-defined]
                    }))
                if blessing_type:
                    # Apply blessing based on type
                    self._apply_blessing(blessing_type)

    def _apply_blessing(self, blessing_type: str) -> None:
        """Apply a blessing to the player based on type."""
        try:
            if blessing_type == "double_score":
                from farkle.blessings import DoubleScoreBlessing
                blessing = DoubleScoreBlessing(duration=1)
                self.active_effects.append(blessing)
                blessing.player = self
                blessing.activate(self.game)
        except Exception:
            pass

    def draw(self, surface):  # type: ignore[override]
        # Player no longer directly renders HUD; PlayerHUDSprite handles display.
        pass

    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        """Reserved for future player HUD interactions (StarterEffect removed)."""
        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize player state to dictionary for saving.
        
        Returns:
            Dictionary containing player state
        """
        return {
            'gold': self.gold,
            'faith': self.faith,
            'temple_income': self.temple_income,
            'active_effects': [
                {
                    'type': effect.__class__.__name__,
                    'name': effect.name,
                    'duration': effect.duration,
                }
                for effect in self.active_effects
            ],
        }
    
    def from_dict(self, data: dict[str, Any]) -> None:
        """Restore player state from saved dictionary.
        
        Args:
            data: Saved player data
        """
        self.gold = data.get('gold', 0)
        self.faith = data.get('faith', 0)
        self.temple_income = data.get('temple_income', 30)
        
        # Active effects are restored separately by SaveManager
        # since they need special handling for activation

