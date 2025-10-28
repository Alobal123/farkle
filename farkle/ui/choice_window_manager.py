"""Manager for handling choice windows in the game."""

from typing import Optional
from farkle.ui.choice_window import ChoiceWindow, ChoiceItem
from farkle.core.game_event import GameEvent, GameEventType


class ChoiceWindowManager:
    """Manages the lifecycle of choice windows."""
    
    def __init__(self, game):
        self.game = game
        self.active_window: Optional[ChoiceWindow] = None
    
    def open_window(self, window: ChoiceWindow):
        """Open a choice window.
        
        Args:
            window: The choice window to open
        """
        # Close any existing window
        if self.active_window and self.active_window.is_open():
            self.active_window.close()
        
        self.active_window = window
        window.open()
        
        # Emit event
        self.game.event_listener.publish(GameEvent(
            GameEventType.CHOICE_WINDOW_OPENED,
            payload={
                "window_type": window.window_type,
                "title": window.title,
                "num_items": len(window.items)
            }
        ))
    
    def close_window(self, window_type: Optional[str] = None):
        """Close the active choice window.
        
        Args:
            window_type: Optional type check - only closes if matches
        """
        if not self.active_window or not self.active_window.is_open():
            return
        
        # Type check if specified
        if window_type and self.active_window.window_type != window_type:
            return
        
        window = self.active_window
        selected_items = window.get_selected_items()
        
        # Execute selections
        for item in selected_items:
            if item.on_select:
                item.on_select(self.game, item.payload)
        
        # Emit close event
        self.game.event_listener.publish(GameEvent(
            GameEventType.CHOICE_WINDOW_CLOSED,
            payload={
                "window_type": window.window_type,
                "selected_count": len(selected_items),
                "selected_ids": [item.id for item in selected_items]
            }
        ))
        
        window.close()
        self.active_window = None  # Clear active window reference
    
    def skip_window(self, window_type: Optional[str] = None):
        """Skip the active choice window without making selections.
        
        Args:
            window_type: Optional type check - only skips if matches
        """
        if not self.active_window or not self.active_window.is_open():
            return
        
        # Type check if specified
        if window_type and self.active_window.window_type != window_type:
            return
        
        if not self.active_window.allow_skip:
            return
        
        window = self.active_window
        
        # Emit close event
        self.game.event_listener.publish(GameEvent(
            GameEventType.CHOICE_WINDOW_CLOSED,
            payload={
                "window_type": window.window_type,
                "selected_count": 0,
                "selected_ids": [],
                "skipped": True
            }
        ))
        
        window.close()
        self.active_window = None  # Clear active window reference
    
    def has_active_window(self) -> bool:
        """Check if there is an active window."""
        return self.active_window is not None and self.active_window.is_open()
    
    def get_active_window(self) -> Optional[ChoiceWindow]:
        """Get the currently active window."""
        if self.active_window and self.active_window.is_open():
            return self.active_window
        return None


__all__ = ["ChoiceWindowManager"]
