from dataclasses import dataclass
from game_object import GameObject
from game_event import GameEvent, GameEventType

@dataclass
class Player(GameObject):
    gold: int = 0
    game: object | None = None

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
                    # Emit GOLD_GAINED event
                    if self.game:
                        from game_event import GameEvent as GE, GameEventType as GET
                        self.game.event_listener.publish(GE(GET.GOLD_GAINED, payload={"amount": gained, "goal_name": goal.name}))
        elif event.type == GameEventType.GOLD_GAINED:
            # Placeholder for future tracking (e.g., achievements)
            pass

    def draw(self, surface):  # type: ignore[override]
        # Player itself has no direct sprite; rendering handled elsewhere.
        return
