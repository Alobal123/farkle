from dataclasses import dataclass, field
from farkle.goals.goal import Goal
from typing import List, Tuple

@dataclass(frozen=True)
class Level:
    """Immutable level definition.

    Multi-goal support:
    goals: list of (name, target_score, mandatory_flag)
      - mandatory goals must all be fulfilled to complete the level
      - optional goals grant bonus points / flavor (future expansion)
    """
    name: str
    max_turns: int
    description: str = ""
    goals: Tuple[Tuple[str, int, bool, int], ...] = ()  # sequence of (goal_name, target, mandatory, reward_gold)

    @staticmethod
    def single(name: str, target_goal: int, max_turns: int, description: str = "", reward_gold: int = 50):
        """Helper to create a single-goal Level definition."""
        # Use the level name as the goal name for display consistency.
        return Level(name=name, max_turns=max_turns, description=description,
                     goals=((name, target_goal, True, reward_gold),))

    @staticmethod
    def advance(prev: 'Level', next_index: int) -> 'Level':
        """Return the next level using progression rules:
        targets += 400 + 50*index; add optional goal every 2 levels; +1 turn every 3 levels;
    (Score multiplier progression removed; now tied to Player abilities.)

        Reward scaling: existing goals' gold increased by 10 * level_index; optional goals get base + scaling.
        """
        base_increase = 400
        new_goals = []
        for name, target, mandatory, reward_gold in prev.goals:
            inc = base_increase + 50 * next_index
            new_goals.append((name, target + inc, mandatory, reward_gold + 10 * next_index))
        if next_index % 2 == 0:
            opt_name = f"Minor Favor {next_index//2}"
            opt_target = 150 + 25 * next_index
            new_goals.append((opt_name, opt_target, False, 25 + 5 * next_index))
        extra_turns = 1 if (next_index % 3 == 0) else 0
        max_turns = prev.max_turns + extra_turns
        return Level(
            name=f"Rite {next_index}",
            max_turns=max_turns,
            description="An intensified supplication to sterner deities.",
            goals=tuple(new_goals)
        )

@dataclass
class LevelState:
    level: Level
    goals: List[Goal] = field(init=False)
    mandatory_indices: List[int] = field(init=False)
    turns_left: int = field(init=False)
    completed: bool = False
    failed: bool = False

    def __post_init__(self):
        self.goals = [Goal(target, name=_n, mandatory=_m, reward_gold=_rg) for (_n, target, _m, _rg) in self.level.goals]
        self.mandatory_indices = [i for i, (_n, _t, m, _rg) in enumerate(self.level.goals) if m]
        self.turns_left = self.level.max_turns

    def reset(self):
        self.goals = [Goal(target, name=_n, mandatory=_m, reward_gold=_rg) for (_n, target, _m, _rg) in self.level.goals]
        self.turns_left = self.level.max_turns
        self.completed = False
        self.failed = False

    def consume_turn(self):
        if self.turns_left > 0:
            self.turns_left -= 1
        if self.turns_left <= 0 and not self._all_mandatory_fulfilled():
            self.failed = True

    def _all_mandatory_fulfilled(self) -> bool:
        return all(self.goals[i].is_fulfilled() for i in self.mandatory_indices)

    def is_active(self) -> bool:
        return not (self.completed or self.failed)
