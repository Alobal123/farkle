"""Generic choice window system for presenting options to the player.

This module provides a general-purpose choice window that can be used for:
- God selection at game start
- Relic shop between levels
- Any future selection screens

The window supports:
- Minimize/maximize to allow inspecting game state
- Multiple choice items with custom rendering
- Event-driven selection and dismissal
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional
from enum import Enum, auto


class ChoiceWindowState(Enum):
    """State of the choice window."""
    CLOSED = auto()      # Window not visible
    MAXIMIZED = auto()   # Window fully visible
    MINIMIZED = auto()   # Window collapsed to corner


@dataclass
class ChoiceItem:
    """A single item that can be selected in a choice window.
    
    This is a generic container that can represent relics, gods, or any other
    selectable option.
    """
    id: str
    name: str
    description: str
    payload: Any  # The actual item (e.g., Relic, God class, etc.)
    on_select: Callable[[Any, Any], None]  # Called when selected: (game, payload) -> None
    
    # Optional fields for different use cases
    cost: Optional[int] = None  # For purchasable items
    icon: Optional[str] = None  # Icon identifier
    enabled: bool = True  # Whether the item can be selected
    effect_text: Optional[str] = None  # Additional effect description


class ChoiceWindow:
    """A generic choice window that can be used for various selection screens.
    
    The window can be minimized to a corner to allow the player to inspect
    the game state before making a decision.
    """
    
    def __init__(
        self,
        title: str,
        items: List[ChoiceItem],
        window_type: str = "generic",
        allow_skip: bool = True,
        allow_minimize: bool = True,
        min_selections: int = 1,
        max_selections: int = 1
    ):
        """Initialize a choice window.
        
        Args:
            title: Title displayed at the top of the window
            items: List of items to choose from
            window_type: Type identifier (e.g., "shop", "god_selection")
            allow_skip: Whether the player can skip without selecting
            allow_minimize: Whether the window can be minimized
            min_selections: Minimum number of selections required
            max_selections: Maximum number of selections allowed
        """
        self.title = title
        self.items = items
        self.window_type = window_type
        self.allow_skip = allow_skip
        self.allow_minimize = allow_minimize
        self.min_selections = min_selections
        self.max_selections = max_selections
        
        self.state = ChoiceWindowState.CLOSED
        self.selected_indices: List[int] = []
    
    def open(self):
        """Open the window in maximized state."""
        self.state = ChoiceWindowState.MAXIMIZED
    
    def close(self):
        """Close the window."""
        self.state = ChoiceWindowState.CLOSED
        self.selected_indices.clear()
    
    def minimize(self):
        """Minimize the window to corner."""
        if self.allow_minimize and self.state == ChoiceWindowState.MAXIMIZED:
            self.state = ChoiceWindowState.MINIMIZED
    
    def maximize(self):
        """Restore window from minimized state."""
        if self.state == ChoiceWindowState.MINIMIZED:
            self.state = ChoiceWindowState.MAXIMIZED
    
    def toggle_minimize(self):
        """Toggle between minimized and maximized."""
        if self.state == ChoiceWindowState.MINIMIZED:
            self.maximize()
        elif self.state == ChoiceWindowState.MAXIMIZED:
            self.minimize()
    
    def is_open(self) -> bool:
        """Check if window is open (maximized or minimized)."""
        return self.state != ChoiceWindowState.CLOSED
    
    def is_maximized(self) -> bool:
        """Check if window is maximized."""
        return self.state == ChoiceWindowState.MAXIMIZED
    
    def is_minimized(self) -> bool:
        """Check if window is minimized."""
        return self.state == ChoiceWindowState.MINIMIZED
    
    def select_item(self, index: int) -> bool:
        """Select an item by index.
        
        Returns:
            True if selection was successful, False otherwise
        """
        if index < 0 or index >= len(self.items):
            return False
        
        if not self.items[index].enabled:
            return False
        
        # Single selection mode
        if self.max_selections == 1:
            self.selected_indices = [index]
            return True
        
        # Multiple selection mode
        if index in self.selected_indices:
            # Deselect
            self.selected_indices.remove(index)
            return True
        else:
            # Select if not at max
            if len(self.selected_indices) < self.max_selections:
                self.selected_indices.append(index)
                return True
        
        return False
    
    def can_confirm(self) -> bool:
        """Check if current selection can be confirmed."""
        return len(self.selected_indices) >= self.min_selections
    
    def get_selected_items(self) -> List[ChoiceItem]:
        """Get currently selected items."""
        return [self.items[i] for i in self.selected_indices if i < len(self.items)]


__all__ = [
    "ChoiceWindow",
    "ChoiceWindowState", 
    "ChoiceItem"
]
