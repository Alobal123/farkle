"""Hades - God of the Underworld and Spirits

Leveling: Gains levels based on Spirit goals completed (max level 3)
- Level 1: 2 spirit goals (+20% to spirit goals)
- Level 2: 4 more spirit goals (6 total) (Sanctify ability - change goal to spirit)
- Level 3: 6 more spirit goals (12 total)

Favor Progression:
- Level 1: +20% scoring bonus to spirit goals
- Level 2: Sanctify ability (1 use) - change a goal's category to spirit
"""

from farkle.gods.gods_manager import God, GOD_MAX_LEVEL
from farkle.core.game_event import GameEvent, GameEventType
from farkle.scoring.score_modifiers import ConditionalScoreModifier, GlobalPartsMultiplier


class Hades(God):
    """Hades grants powers related to the underworld, death, and spirits."""
    
    # Goals required per level: [level 0->1, level 1->2, level 2->3]
    GOALS_PER_LEVEL = [2, 4, 6]
    
    def __init__(self, game=None):
        super().__init__(name="Hades", game=game)
        self.level = 0  # Start at level 0
        self.goals_completed = 0  # Track spirit goals completed
    
    def on_activate(self, game):  # type: ignore[override]
        """Called when Hades is added to worshipped gods."""
        super().on_activate(game)
    
    def on_deactivate(self, game):  # type: ignore[override]
        """Called when Hades is removed from worshipped gods."""
        super().on_deactivate(game)
    
    def on_event(self, event: GameEvent):  # type: ignore[override]
        """Listen for Spirit goal completions and reward events."""
        if event.type == GameEventType.GOAL_FULFILLED:
            goal = event.get('goal')
            if goal and hasattr(goal, 'category'):
                category = getattr(goal, 'category', '')
                if category == 'spirit':
                    self._level_up_from_goal()
        
        # Level 3: Double rewards for spirit goals
        elif self.level >= 3:
            if event.type == GameEventType.GOLD_GAINED:
                self._maybe_double_gold_reward(event)
            elif event.type == GameEventType.INCOME_GAINED:
                self._maybe_double_income_reward(event)
            elif event.type == GameEventType.FAITH_GAINED:
                self._maybe_double_faith_reward(event)
            elif event.type == GameEventType.BLESSING_GAINED:
                self._maybe_double_blessing_reward(event)
    
    def _level_up_from_goal(self):
        """Level up when a spirit goal is completed."""
        self.goals_completed += 1  # Always increment counter
        
        if self.level >= GOD_MAX_LEVEL:
            return
        
        # Check if we have enough goals for next level
        goals_needed = self._goals_needed_for_level(self.level + 1)
        if self.goals_completed >= goals_needed:
            old_level = self.level
            self.level += 1
            
            # Add level 1 bonus: +20% to spirit goals
            if self.level == 1:
                self._add_level_1_bonus()
            
            # Add level 2 ability: Sanctify goal category
            if self.level == 2:
                self._add_level_2_ability()
            
            # Level 3 enables reward doubling (passive, handled in on_event)
            if self.level == 3:
                pass  # Reward doubling is automatic via on_event listening
            
            try:
                self.emit(self.game, GameEventType.GOD_LEVEL_UP, {
                    "god_name": self.name,
                    "old_level": old_level,
                    "new_level": self.level,
                    "category": "spirit",
                    "goals_completed": self.goals_completed,
                    "goals_needed": goals_needed
                })
            except Exception:
                pass
    
    def _add_level_1_bonus(self):
        """Add +20% scoring bonus to spirit goals."""
        try:
            # Create a conditional modifier that only applies to spirit category goals
            category_predicate = lambda ctx: getattr(getattr(ctx, 'goal', None), 'category', '') == 'spirit'
            modifier = ConditionalScoreModifier(
                GlobalPartsMultiplier(1.2, priority=58, description="Hades Level 1"),
                predicate=category_predicate
            )
            
            # Emit SCORE_MODIFIER_ADDED event
            self.emit(self.game, GameEventType.SCORE_MODIFIER_ADDED, {
                "god": self.name,
                "level": 1,
                "modifier_type": "ConditionalScoreModifier",
                "description": "+20% to spirit goals",
                "data": {"category": "spirit", "mult": 1.2}
            })
            
            # Add to god's modifier chain for tracking
            self.modifier_chain.add(modifier)
        except Exception:
            pass
    
    def _add_level_2_ability(self):
        """Add Sanctify ability to change goal categories to spirit."""
        try:
            from farkle.abilities.sanctify_ability import SanctifyAbility
            
            # Create the sanctify ability
            ability = SanctifyAbility(
                god_name=self.name,
                god_category="spirit",
                charges_per_level=1
            )
            
            # Register with ability manager
            ability_manager = getattr(self.game, 'ability_manager', None)
            if ability_manager:
                ability_manager.register(ability)
            
            # Don't emit ABILITY_CHARGES_ADDED - the ability already has its charges
        except Exception:
            pass
    
    def _maybe_double_gold_reward(self, event: GameEvent):
        """Double gold rewards from spirit goals at level 3."""
        source = event.get("source", "")
        category = event.get("goal_category", "")
        amount = event.get("amount", 0)
        
        # Only double goal rewards (not temple income or god bonuses)
        if source == "goal_reward" and category == "spirit" and amount > 0:
            try:
                self.emit(self.game, GameEventType.GOLD_REWARDED, {
                    "amount": amount,
                    "source": "god_bonus",
                    "god_name": self.name,
                    "original_category": category
                })
            except Exception:
                pass
    
    def _maybe_double_income_reward(self, event: GameEvent):
        """Double income rewards from spirit goals at level 3."""
        source = event.get("source", "")
        category = event.get("goal_category", "")
        amount = event.get("amount", 0)
        
        if source == "goal_reward" and category == "spirit" and amount > 0:
            try:
                player = getattr(self.game, 'player', None)
                new_total = getattr(player, 'temple_income', 0) + amount if player else amount
                
                self.emit(self.game, GameEventType.INCOME_REWARDED, {
                    "amount": amount,
                    "source": "god_bonus",
                    "god_name": self.name,
                    "original_category": category,
                    "new_total": new_total
                })
            except Exception:
                pass
    
    def _maybe_double_faith_reward(self, event: GameEvent):
        """Double faith rewards from spirit goals at level 3."""
        source = event.get("source", "")
        category = event.get("goal_category", "")
        amount = event.get("amount", 0)
        
        if source == "goal_reward" and category == "spirit" and amount > 0:
            try:
                self.emit(self.game, GameEventType.FAITH_REWARDED, {
                    "amount": amount,
                    "source": "god_bonus",
                    "god_name": self.name,
                    "original_category": category
                })
            except Exception:
                pass
    
    def _maybe_double_blessing_reward(self, event: GameEvent):
        """Double blessing rewards from spirit goals at level 3 (extends duration)."""
        source = event.get("source", "")
        category = event.get("goal_category", "")
        blessing_type = event.get("blessing_type", "")
        
        # Only double goal blessings (not god bonuses to avoid infinite loop)
        if source == "goal_reward" and category == "spirit" and blessing_type:
            try:
                self.emit(self.game, GameEventType.BLESSING_REWARDED, {
                    "blessing_type": blessing_type,
                    "source": "god_bonus",
                    "god_name": self.name,
                    "original_category": category
                })
            except Exception:
                pass
    
    def _goals_needed_for_level(self, target_level: int) -> int:
        """Calculate cumulative goals needed to reach target_level."""
        if target_level <= 0:
            return 0
        if target_level > len(self.GOALS_PER_LEVEL):
            target_level = len(self.GOALS_PER_LEVEL)
        return sum(self.GOALS_PER_LEVEL[:target_level])


__all__ = ["Hades"]
