"""Sanctify Ability - Change a goal's category to match the god's category.

This is a level 2 god ability that allows the player to select a goal
and change its category to match the god's category (nature, warfare, spirit, or commerce).
"""

from __future__ import annotations
from farkle.abilities.ability import TargetedAbility
from farkle.core.game_event import GameEvent, GameEventType


class SanctifyAbility(TargetedAbility):
    """Targeted ability to change a goal's category.
    
    Args:
        god_name: Name of the god granting this ability
        god_category: Category to change goals to (nature, warfare, spirit, commerce)
        charges_per_level: Number of uses per level (default 1)
    """
    
    def __init__(self, god_name: str, god_category: str, charges_per_level: int = 1):
        # Create unique id based on god name
        ability_id = f"sanctify_{god_category}"
        super().__init__(
            id=ability_id,
            name=f"Sanctify ({god_name})",
            charges_per_level=charges_per_level,
            selectable=True,
            target_type='goal',
            description=f"Change a goal's category to {god_category}."
        )
        self.god_name = god_name
        self.god_category = god_category
    
    def can_activate(self, ctx) -> bool:
        """Can activate if there are available charges and goals to sanctify."""
        if not super().can_activate(ctx):
            return False
        
        # Check if there are any goals that aren't already the target category
        try:
            goals = ctx.game.level_state.goals
            for goal in goals:
                if goal.category != self.god_category:
                    return True
        except Exception:
            pass
        
        return False
    
    def execute(self, ctx, target=None) -> bool:
        """Execute the sanctify ability on the selected goal.
        
        Args:
            ctx: Ability context with game reference
            target: Index of the goal to sanctify
        
        Returns:
            True if successful, False otherwise
        """
        if target is None:
            return False
        
        try:
            goal_index = int(target)  # type: ignore[arg-type]
        except Exception:
            return False
        
        game = ctx.game
        
        # Validate goal index
        try:
            goals = game.level_state.goals
            if goal_index < 0 or goal_index >= len(goals):
                game.set_message("Invalid goal selection.")
                return False
            
            goal = goals[goal_index]
            
            # Check if goal is already the target category
            if goal.category == self.god_category:
                game.set_message(f"Goal already {self.god_category} category.")
                return False
            
            # Store old category for event
            old_category = goal.category
            
            # Change the goal's category
            goal.category = self.god_category
            
            # Consume the charge
            self.consume()
            
            # Emit events
            try:
                game.event_listener.publish(GameEvent(
                    GameEventType.ABILITY_EXECUTED,
                    payload={
                        "ability": self.id,
                        "target_index": goal_index,
                        "god": self.god_name,
                        "old_category": old_category,
                        "new_category": self.god_category
                    }
                ))
            except Exception:
                pass
            
            # Update message
            game.set_message(f"Goal sanctified to {self.god_category} by {self.god_name}!")
            
            return True
            
        except Exception as e:
            try:
                game.set_message(f"Failed to sanctify goal: {str(e)}")
            except Exception:
                pass
            return False
