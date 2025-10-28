"""Base class for category-based gods (Demeter, Ares, Hades, Hermes).

All four gods follow the same pattern:
- Level up based on category-specific goal completions
- Level 1: +20% scoring bonus to their category
- Level 2: Sanctify ability (change goal category)
- Level 3: Double all rewards from their category
"""

from farkle.gods.gods_manager import God, GOD_MAX_LEVEL
from farkle.core.game_event import GameEvent, GameEventType
from farkle.scoring.score_modifiers import ConditionalScoreModifier, GlobalPartsMultiplier


class CategoryGod(God):
    """Base class for category-specific gods."""
    
    # Goals required per level: [level 0->1, level 1->2, level 2->3]
    GOALS_PER_LEVEL = [2, 4, 6]
    
    def __init__(self, name: str, category: str, lore: str, game=None):
        super().__init__(name=name, game=game)
        self.category = category
        self.lore = lore
        self.level = 0  # Start at level 0
        self.goals_completed = 0  # Track category goals completed
    
    def get_tooltip_lines(self):
        """Return tooltip lines for this god."""
        lines = []
        
        # Lore
        lines.append(self.lore)
        lines.append("")  # Blank separator
        
        # Progress line
        lines.append(f"Progress: {self.goals_completed} {self.category} goals completed")
        lines.append("")  # Blank separator
        
        # Level progression
        level_1_prefix = "[X]" if self.level >= 1 else "[ ]"
        lines.append(f"{level_1_prefix} Level 1 - 2 {self.category} goals - +20% to {self.category} goals")
        
        level_2_prefix = "[X]" if self.level >= 2 else "[ ]"
        lines.append(f"{level_2_prefix} Level 2 - 6 {self.category} goals - Sanctify ability")
        
        level_3_prefix = "[X]" if self.level >= 3 else "[ ]"
        lines.append(f"{level_3_prefix} Level 3 - 12 {self.category} goals - Double {self.category} rewards")
        
        return lines
    
    def on_activate(self, game):  # type: ignore[override]
        """Called when god is added to worshipped gods."""
        super().on_activate(game)
    
    def on_deactivate(self, game):  # type: ignore[override]
        """Called when god is removed from worshipped gods."""
        super().on_deactivate(game)
    
    def on_event(self, event: GameEvent):  # type: ignore[override]
        """Listen for category goal completions and reward events."""
        if event.type == GameEventType.GOAL_FULFILLED:
            goal = event.get('goal')
            if goal and hasattr(goal, 'category'):
                category = getattr(goal, 'category', '')
                if category == self.category:
                    self._level_up_from_goal()
        
        # Level 3: Double rewards for category goals
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
        """Increment goals_completed and level up if threshold reached."""
        self.goals_completed += 1
        
        # Check if we should level up
        cumulative = 0
        for level_idx in range(GOD_MAX_LEVEL):
            cumulative += self.GOALS_PER_LEVEL[level_idx]
            if self.goals_completed >= cumulative and self.level == level_idx:
                self.level = level_idx + 1
                self._emit_level_up_event()
                
                # Level 1: Add scoring bonus
                if self.level == 1:
                    self._add_level_1_bonus()
                
                # Level 2: Grant sanctify ability
                if self.level == 2:
                    self._grant_sanctify_ability()
                break
    
    def _emit_level_up_event(self):
        """Emit GOD_LEVEL_UP event."""
        if not self.game:
            return
        try:
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOD_LEVEL_UP,
                payload={
                    "god_name": self.name,
                    "old_level": self.level - 1,
                    "new_level": self.level,
                    "category": self.category,
                    "goals_completed": self.goals_completed,
                    "goals_needed": sum(self.GOALS_PER_LEVEL[:self.level])
                }
            ))
        except Exception:
            pass
    
    def _grant_sanctify_ability(self):
        """Grant the Sanctify ability at level 2."""
        if not self.game:
            return
        try:
            from farkle.abilities.sanctify_ability import SanctifyAbility
            ability = SanctifyAbility(
                god_name=self.name,
                god_category=self.category,
                charges_per_level=1
            )
            self.game.ability_manager.register(ability)
            
            # Rebuild UI buttons to include the new ability button
            if hasattr(self.game, '_rebuild_ui_buttons'):
                self.game._rebuild_ui_buttons()
        except Exception:
            pass
    
    def _add_level_1_bonus(self):
        """Add +20% scoring bonus to category goals at level 1."""
        if not self.game:
            return
        try:
            # Create a conditional modifier that only applies to this category
            category_predicate = lambda ctx: getattr(getattr(ctx, 'goal', None), 'category', '') == self.category
            modifier = ConditionalScoreModifier(
                GlobalPartsMultiplier(1.2, priority=58, description=f"{self.name} Level 1"),
                predicate=category_predicate
            )
            
            # Emit SCORE_MODIFIER_ADDED event
            self.game.event_listener.publish(GameEvent(
                GameEventType.SCORE_MODIFIER_ADDED,
                payload={
                    "god": self.name,
                    "level": 1,
                    "modifier_type": "ConditionalScoreModifier",
                    "description": f"+20% to {self.category} goals",
                    "data": {"category": self.category, "mult": 1.2}
                }
            ))
            
            # Add to scoring manager
            self.game.scoring_manager.modifier_chain.add(modifier)
        except Exception:
            pass

    
    def _maybe_double_gold_reward(self, event: GameEvent):
        """Double gold rewards from matching category goals."""
        if event.get('source') != 'goal_reward':
            return
        if event.get('goal_category') != self.category:
            return
        
        amount = event.get('amount', 0)
        if amount <= 0:
            return
        
        # Emit another GOLD_REWARDED event with god_bonus source
        goal_name = event.get('goal_name', '')
        try:
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOLD_REWARDED,
                payload={
                    'amount': amount,
                    'source': 'god_bonus',
                    'goal_name': goal_name,
                    'goal_category': self.category,
                    'god_name': self.name
                }
            ))
        except Exception:
            pass
    
    def _maybe_double_income_reward(self, event: GameEvent):
        """Double income rewards from matching category goals."""
        if event.get('source') != 'goal_reward':
            return
        if event.get('goal_category') != self.category:
            return
        
        amount = event.get('amount', 0)
        if amount <= 0:
            return
        
        goal_name = event.get('goal_name', '')
        try:
            self.game.event_listener.publish(GameEvent(
                GameEventType.INCOME_REWARDED,
                payload={
                    'amount': amount,
                    'source': 'god_bonus',
                    'goal_name': goal_name,
                    'goal_category': self.category,
                    'god_name': self.name
                }
            ))
        except Exception:
            pass
    
    def _maybe_double_faith_reward(self, event: GameEvent):
        """Double faith rewards from matching category goals."""
        if event.get('source') != 'goal_reward':
            return
        if event.get('goal_category') != self.category:
            return
        
        amount = event.get('amount', 0)
        if amount <= 0:
            return
        
        goal_name = event.get('goal_name', '')
        try:
            self.game.event_listener.publish(GameEvent(
                GameEventType.FAITH_REWARDED,
                payload={
                    'amount': amount,
                    'source': 'god_bonus',
                    'goal_name': goal_name,
                    'goal_category': self.category,
                    'god_name': self.name
                }
            ))
        except Exception:
            pass
    
    def _maybe_double_blessing_reward(self, event: GameEvent):
        """Double blessing rewards from matching category goals."""
        if event.get('source') != 'goal_reward':
            return
        if event.get('goal_category') != self.category:
            return
        
        blessing_type = event.get('blessing_type')
        if not blessing_type:
            return
        
        goal_name = event.get('goal_name', '')
        try:
            self.game.event_listener.publish(GameEvent(
                GameEventType.BLESSING_REWARDED,
                payload={
                    'blessing_type': blessing_type,
                    'source': 'god_bonus',
                    'goal_name': goal_name,
                    'goal_category': self.category,
                    'god_name': self.name
                }
            ))
        except Exception:
            pass
