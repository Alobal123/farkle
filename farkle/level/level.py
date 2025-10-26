from dataclasses import dataclass, field
from farkle.goals.goal import Goal
from typing import List, Tuple, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from farkle.core.random_source import RandomSource

@dataclass(frozen=True)
class Level:
    """Immutable level definition.

    Multi-goal support:
    goals: list of (name, target_score, is_disaster_flag)
      - disaster goals must all be fulfilled to complete the level
      - petition goals grant bonus points / flavor (future expansion)
    """
    name: str
    max_turns: int
    description: str = ""
    goals: Tuple[Tuple[str, int, bool, int, str, str], ...] = ()  # sequence of (goal_name, target, is_disaster, reward_gold, flavor_text, category)

    @staticmethod
    def single(name: str, target_goal: int, max_turns: int, description: str = "", reward_gold: int = 50, rng: 'RandomSource | random.Random | None' = None):
        """Helper to create a single-goal Level definition with petitions.
        
        First level starts with a disaster and 2 petitions.
        """
        # Import here to avoid circular dependency
        from farkle.level.lore_loader import load_petitions, load_disasters
        
        # Use provided RNG or create a new one
        if rng is None:
            rng = random.Random()
        
        # Start with a disaster
        goals_list = []
        disasters = load_disasters()
        if disasters:
            disaster = rng.choice(disasters)
            goals_list.append((disaster['title'], target_goal, True, reward_gold, disaster.get('text', ''), disaster.get('category', '')))
        else:
            # Fallback to original behavior
            goals_list.append((name, target_goal, True, reward_gold, description, ''))
        
        # Add 2 petitions for the first level
        petitions = load_petitions()
        if petitions:
            # Select 2 random petitions
            selected = rng.sample(petitions, min(2, len(petitions)))
            for i, petition in enumerate(selected):
                opt_name = petition['title']
                opt_target = 150 + 25 * i  # Progressive targets
                opt_reward = 25 + 5 * i
                opt_flavor = petition.get('text', '')  # Use 'text' field from petitions2.json
                opt_category = petition.get('category', '')
                goals_list.append((opt_name, opt_target, False, opt_reward, opt_flavor, opt_category))
        
        return Level(name=name, max_turns=max_turns, description=description,
                     goals=tuple(goals_list))

    @staticmethod
    def advance(prev: 'Level', next_index: int, rng: 'RandomSource | random.Random | None' = None) -> 'Level':
        """Return the next level using progression rules:
        - Disasters: A new disaster is chosen each level. Target score increases.
        - Petitions: Progressive count - starts at 2, +1 every 2 levels, capped at 4
          Level 1: 2 petitions
          Level 2-3: 2 petitions
          Level 4-5: 3 petitions
          Level 6-7: 4 petitions
          Level 8+: 4 petitions
        - Turns: +1 turn every 3 levels
        """
        # Import here to avoid circular dependency
        from farkle.level.lore_loader import load_petitions, load_disasters
        
        # Use provided RNG or create a new one
        if rng is None:
            rng = random.Random()
        
        base_increase = 400
        new_goals = []
        
        # Select a new disaster
        disasters = load_disasters()
        if disasters:
            # Find the old disaster's target to calculate the new one
            old_disaster_target = 0
            for _, target, is_disaster, _, _, _ in prev.goals:
                if is_disaster:
                    old_disaster_target = target
                    break
            
            new_target = old_disaster_target + base_increase + 50 * next_index
            new_reward = 50 + 10 * next_index
            
            disaster = rng.choice(disasters)
            new_goals.append((disaster['title'], new_target, True, new_reward, disaster.get('text', ''), disaster.get('category', '')))
        
        # Calculate how many petitions this level should have
        # Formula: min(2 + ((next_index - 1) // 2), 4)
        petition_count = min(2 + ((next_index - 1) // 2), 4)
        
        # Generate new petitions
        petitions = load_petitions()
        if petitions:
            # Select random petitions (avoiding duplicates)
            selected = rng.sample(petitions, min(petition_count, len(petitions)))
            for i, petition in enumerate(selected):
                opt_name = petition['title']
                opt_target = 150 + 25 * next_index + 10 * i
                opt_reward = 25 + 5 * next_index + 2 * i
                opt_flavor = petition.get('text', '')  # Use 'text' field from petitions2.json
                opt_category = petition.get('category', '')
                new_goals.append((opt_name, opt_target, False, opt_reward, opt_flavor, opt_category))
        
        # Add extra turns every 3 levels
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
    disaster_indices: List[int] = field(init=False)
    turns_left: int = field(init=False)
    completed: bool = False
    failed: bool = False

    def __post_init__(self):
        self.goals = [Goal(target, name=_n, is_disaster=_m, reward_gold=_rg, flavor=_f, category=_c) for (_n, target, _m, _rg, _f, _c) in self.level.goals]
        self.disaster_indices = [i for i, (_n, _t, m, _rg, _f, _c) in enumerate(self.level.goals) if m]
        self.turns_left = self.level.max_turns

    def reset(self):
        self.goals = [Goal(target, name=_n, is_disaster=_m, reward_gold=_rg, flavor=_f, category=_c) for (_n, target, _m, _rg, _f, _c) in self.level.goals]
        self.turns_left = self.level.max_turns
        self.completed = False
        self.failed = False

    def consume_turn(self):
        if self.turns_left > 0:
            self.turns_left -= 1
        if self.turns_left <= 0 and not self._all_disasters_fulfilled():
            self.failed = True

    def _all_disasters_fulfilled(self) -> bool:
        return all(self.goals[i].is_fulfilled() for i in self.disaster_indices)

    def is_active(self) -> bool:
        return not (self.completed or self.failed)
