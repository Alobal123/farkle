"""Tests for the choice window system."""

import unittest
import pygame
from farkle.game import Game
from farkle.ui.choice_window import ChoiceWindow, ChoiceItem, ChoiceWindowState
from farkle.ui.choice_window_manager import ChoiceWindowManager
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class ChoiceWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()
    
    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=42)
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))
    
    def test_choice_window_basic_creation(self):
        """Test creating a basic choice window."""
        items = [
            ChoiceItem(
                id="item1",
                name="Test Item 1",
                description="First test item",
                payload={"data": 1},
                on_select=lambda g, p: None
            ),
            ChoiceItem(
                id="item2",
                name="Test Item 2",
                description="Second test item",
                payload={"data": 2},
                on_select=lambda g, p: None
            )
        ]
        
        window = ChoiceWindow(
            title="Test Window",
            items=items,
            window_type="test"
        )
        
        self.assertEqual(window.title, "Test Window")
        self.assertEqual(len(window.items), 2)
        self.assertEqual(window.state, ChoiceWindowState.CLOSED)
    
    def test_choice_window_open_close(self):
        """Test opening and closing a choice window."""
        items = [
            ChoiceItem(
                id="item1",
                name="Test Item",
                description="Test",
                payload={},
                on_select=lambda g, p: None
            )
        ]
        
        window = ChoiceWindow(title="Test", items=items)
        
        # Initially closed
        self.assertFalse(window.is_open())
        self.assertEqual(window.state, ChoiceWindowState.CLOSED)
        
        # Open it
        window.open()
        self.assertTrue(window.is_open())
        self.assertTrue(window.is_maximized())
        self.assertEqual(window.state, ChoiceWindowState.MAXIMIZED)
        
        # Close it
        window.close()
        self.assertFalse(window.is_open())
        self.assertEqual(window.state, ChoiceWindowState.CLOSED)
    
    def test_choice_window_minimize_maximize(self):
        """Test minimizing and maximizing a choice window."""
        items = [
            ChoiceItem(
                id="item1",
                name="Test Item",
                description="Test",
                payload={},
                on_select=lambda g, p: None
            )
        ]
        
        window = ChoiceWindow(title="Test", items=items, allow_minimize=True)
        window.open()
        
        # Should be maximized initially
        self.assertTrue(window.is_maximized())
        self.assertFalse(window.is_minimized())
        
        # Minimize it
        window.minimize()
        self.assertFalse(window.is_maximized())
        self.assertTrue(window.is_minimized())
        self.assertTrue(window.is_open())  # Still open, just minimized
        
        # Maximize it again
        window.maximize()
        self.assertTrue(window.is_maximized())
        self.assertFalse(window.is_minimized())
    
    def test_choice_window_toggle_minimize(self):
        """Test toggling minimize state."""
        items = [
            ChoiceItem(
                id="item1",
                name="Test Item",
                description="Test",
                payload={},
                on_select=lambda g, p: None
            )
        ]
        
        window = ChoiceWindow(title="Test", items=items, allow_minimize=True)
        window.open()
        
        # Toggle to minimized
        window.toggle_minimize()
        self.assertTrue(window.is_minimized())
        
        # Toggle back to maximized
        window.toggle_minimize()
        self.assertTrue(window.is_maximized())
    
    def test_choice_window_single_selection(self):
        """Test selecting a single item."""
        items = [
            ChoiceItem(id="item1", name="Item 1", description="Test", payload={}, on_select=lambda g, p: None),
            ChoiceItem(id="item2", name="Item 2", description="Test", payload={}, on_select=lambda g, p: None),
            ChoiceItem(id="item3", name="Item 3", description="Test", payload={}, on_select=lambda g, p: None)
        ]
        
        window = ChoiceWindow(title="Test", items=items, max_selections=1)
        
        # Select first item
        success = window.select_item(0)
        self.assertTrue(success)
        self.assertEqual(window.selected_indices, [0])
        
        # Select second item (should replace first)
        success = window.select_item(1)
        self.assertTrue(success)
        self.assertEqual(window.selected_indices, [1])
    
    def test_choice_window_multiple_selection(self):
        """Test selecting multiple items."""
        items = [
            ChoiceItem(id="item1", name="Item 1", description="Test", payload={}, on_select=lambda g, p: None),
            ChoiceItem(id="item2", name="Item 2", description="Test", payload={}, on_select=lambda g, p: None),
            ChoiceItem(id="item3", name="Item 3", description="Test", payload={}, on_select=lambda g, p: None)
        ]
        
        window = ChoiceWindow(title="Test", items=items, max_selections=2)
        
        # Select first item
        window.select_item(0)
        self.assertEqual(window.selected_indices, [0])
        
        # Select second item
        window.select_item(1)
        self.assertEqual(len(window.selected_indices), 2)
        self.assertIn(0, window.selected_indices)
        self.assertIn(1, window.selected_indices)
        
        # Try to select third item (should fail - max is 2)
        success = window.select_item(2)
        self.assertFalse(success)
        self.assertEqual(len(window.selected_indices), 2)
    
    def test_choice_window_can_confirm(self):
        """Test can_confirm logic."""
        items = [
            ChoiceItem(id="item1", name="Item 1", description="Test", payload={}, on_select=lambda g, p: None),
            ChoiceItem(id="item2", name="Item 2", description="Test", payload={}, on_select=lambda g, p: None)
        ]
        
        # Require at least 1 selection
        window = ChoiceWindow(title="Test", items=items, min_selections=1)
        self.assertFalse(window.can_confirm())
        
        window.select_item(0)
        self.assertTrue(window.can_confirm())
    
    def test_choice_window_manager_open_emits_event(self):
        """Test that opening a window emits an event."""
        manager = ChoiceWindowManager(self.game)
        
        items = [
            ChoiceItem(id="item1", name="Item 1", description="Test", payload={}, on_select=lambda g, p: None)
        ]
        
        window = ChoiceWindow(title="Test Window", items=items, window_type="test")
        manager.open_window(window)
        
        # Check that CHOICE_WINDOW_OPENED event was emitted
        opened_events = [e for e in self.events if e.type == GameEventType.CHOICE_WINDOW_OPENED]
        self.assertEqual(len(opened_events), 1)
        self.assertEqual(opened_events[0].get("window_type"), "test")
        self.assertEqual(opened_events[0].get("title"), "Test Window")
    
    def test_choice_window_manager_close_executes_selections(self):
        """Test that closing executes selected items."""
        manager = ChoiceWindowManager(self.game)
        
        executed = []
        
        def on_select(game, payload):
            executed.append(payload)
        
        items = [
            ChoiceItem(id="item1", name="Item 1", description="Test", payload={"id": 1}, on_select=on_select),
            ChoiceItem(id="item2", name="Item 2", description="Test", payload={"id": 2}, on_select=on_select)
        ]
        
        window = ChoiceWindow(title="Test", items=items, window_type="test")
        manager.open_window(window)
        
        # Select first item
        window.select_item(0)
        
        # Close window
        manager.close_window()
        
        # Check that on_select was called
        self.assertEqual(len(executed), 1)
        self.assertEqual(executed[0]["id"], 1)
        
        # Check that window is closed
        self.assertFalse(manager.has_active_window())


if __name__ == '__main__':
    unittest.main()
