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
    goals: Tuple[Tuple[str, int, bool, int, int, str, str, str], ...] = ()  # sequence of (goal_name, target, is_disaster, reward_gold, reward_income, flavor_text, category, persona)

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
            # Disasters have no reward - they just advance to the next level
            goals_list.append((disaster['title'], target_goal, True, 0, 0, disaster.get('text', ''), disaster.get('category', ''), ''))
        else:
            # Fallback to original behavior
            goals_list.append((name, target_goal, True, 0, 0, description, '', ''))
        
        # Add 2 petitions for the first level
        petitions = load_petitions()
        if petitions:
            # Filter to only petitions with rewards (merchant or nobleman)
            petitions_with_rewards = [p for p in petitions if p.get('persona') in ('merchant', 'nobleman')]
            
            if petitions_with_rewards:
                # Select 2 random petitions from those with rewards
                selected = rng.sample(petitions_with_rewards, min(2, len(petitions_with_rewards)))
                for i, petition in enumerate(selected):
                    opt_name = petition['title']
                    opt_target = 150 + 25 * i  # Progressive targets
                    opt_flavor = petition.get('text', '')
                    opt_category = petition.get('category', '')
                    opt_persona = petition.get('persona', '')
                    
                    # Set rewards based on persona
                    opt_reward_gold = 0
                    opt_reward_income = 0
                    if opt_persona == 'merchant':
                        # Merchants give gold (scaled with level progression)
                        opt_reward_gold = 25 + 5 * i
                    elif opt_persona == 'nobleman':
                        # Noblemen increase income by 5 (not scaled)
                        opt_reward_income = 5
                    
                    goals_list.append((opt_name, opt_target, False, opt_reward_gold, opt_reward_income, opt_flavor, opt_category, opt_persona))
        
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
            for _, target, is_disaster, _, _, _, _, _ in prev.goals:
                if is_disaster:
                    old_disaster_target = target
                    break
            
            new_target = old_disaster_target + base_increase + 50 * next_index
            
            disaster = rng.choice(disasters)
            # Disasters have no reward - they just advance to the next level
            new_goals.append((disaster['title'], new_target, True, 0, 0, disaster.get('text', ''), disaster.get('category', ''), ''))
        
        # Calculate how many petitions this level should have
        # Formula: min(2 + ((next_index - 1) // 2), 4)
        petition_count = min(2 + ((next_index - 1) // 2), 4)
        
        # Generate new petitions
        petitions = load_petitions()
        if petitions:
            # Filter to only petitions with rewards (merchant or nobleman)
            petitions_with_rewards = [p for p in petitions if p.get('persona') in ('merchant', 'nobleman')]
            
            if petitions_with_rewards:
                # Select random petitions (avoiding duplicates)
                selected = rng.sample(petitions_with_rewards, min(petition_count, len(petitions_with_rewards)))
                for i, petition in enumerate(selected):
                    opt_name = petition['title']
                    opt_target = 150 + 25 * next_index + 10 * i
                    opt_flavor = petition.get('text', '')
                    opt_category = petition.get('category', '')
                    opt_persona = petition.get('persona', '')
                    
                    # Set rewards based on persona
                    opt_reward_gold = 0
                    opt_reward_income = 0
                    if opt_persona == 'merchant':
                        # Merchants give gold (scaled with level progression)
                        opt_reward_gold = 25 + 5 * next_index + 2 * i
                    elif opt_persona == 'nobleman':
                        # Noblemen increase income by 5 (not scaled)
                        opt_reward_income = 5
                    
                    new_goals.append((opt_name, opt_target, False, opt_reward_gold, opt_reward_income, opt_flavor, opt_category, opt_persona))
        
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
        self.goals = [Goal(target, name=_n, is_disaster=_m, reward_gold=_rg, reward_income=_ri, flavor=_f, category=_c, persona=_p) 
                      for (_n, target, _m, _rg, _ri, _f, _c, _p) in self.level.goals]
        self.disaster_indices = [i for i, (_n, _t, m, _rg, _ri, _f, _c, _p) in enumerate(self.level.goals) if m]
        self.turns_left = self.level.max_turns

    def reset(self):
        self.goals = [Goal(target, name=_n, is_disaster=_m, reward_gold=_rg, reward_income=_ri, flavor=_f, category=_c, persona=_p) 
                      for (_n, target, _m, _rg, _ri, _f, _c, _p) in self.level.goals]
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
