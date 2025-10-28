"""Test that god selection window opens at game start."""

import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType


class GodSelectionStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        # Create game without auto-initialization to control the startup sequence
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1, auto_initialize=False)
        
        # Now manually initialize to trigger god selection
        self.game.initialize()
        
        # Subscribe to events after initialization
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))

    def test_game_starts_with_no_gods(self):
        """Game should start with empty worshipped gods list."""
        self.assertEqual(len(self.game.gods.worshipped), 0, 
                        "Game should start with no gods before selection")

    def test_choice_window_opens_at_startup(self):
        """Choice window should open automatically at game start."""
        # Since we subscribe after initialization, check window state directly
        self.assertIsNotNone(self.game.choice_window_manager.active_window,
                            "Choice window should be open")
        self.assertTrue(self.game.choice_window_manager.active_window.is_open(),
                       "Choice window should be in open state")

    def test_choice_window_has_three_random_god_options(self):
        """God selection window should offer 3 random gods to choose from."""
        self.assertIsNotNone(self.game.choice_window_manager.active_window, 
                            "Choice window should be open")
        
        window = self.game.choice_window_manager.active_window
        self.assertEqual(len(window.items), 3, 
                        "Should have 3 god options (randomly selected)")
        
        # Verify all are valid gods
        god_names = {item.name for item in window.items}
        all_possible_gods = {"Demeter", "Ares", "Hades", "Hermes"}
        self.assertTrue(god_names.issubset(all_possible_gods), 
                        "All offered gods should be valid gods")
        self.assertEqual(len(god_names), 3,
                        "Should offer exactly 3 unique gods")

    def test_god_selection_requires_exactly_one_god(self):
        """Player must select exactly 1 god (auto-confirms)."""
        window = self.game.choice_window_manager.active_window
        self.assertEqual(window.min_selections, 1, 
                        "Must select exactly 1 god")
        self.assertEqual(window.max_selections, 1, 
                        "Can only select 1 god (auto-confirms)")
        
        # Cannot confirm with no selections
        self.assertFalse(window.can_confirm(),
                        "Should not be able to confirm with 0 selections")

    def test_god_selection_cannot_be_skipped(self):
        """Player cannot skip god selection."""
        window = self.game.choice_window_manager.active_window
        self.assertFalse(window.allow_skip, 
                        "God selection should not be skippable")

    def test_selecting_god_adds_to_worshipped(self):
        """Selecting a god and confirming should add it to worshipped gods."""
        window = self.game.choice_window_manager.active_window
        
        # Select first item (whichever god it is)
        first_god = window.items[0]
        
        # Find the choice window sprite and simulate click on first god card
        choice_window_sprite = None
        for sprite in self.game.renderer.sprite_groups['modal']:
            if hasattr(sprite, 'choice_window') and sprite.choice_window == window:
                choice_window_sprite = sprite
                break
        
        self.assertIsNotNone(choice_window_sprite, "Should find choice window sprite")
        
        # Get the button rect for first item (after sync to ensure buttons exist)
        choice_window_sprite.sync_from_logical()
        self.assertTrue(len(choice_window_sprite._item_button_rects) > 0, "Should have item buttons")
        
        first_button_idx, first_button_rect = choice_window_sprite._item_button_rects[0]
        click_pos = first_button_rect.center
        
        # Simulate click on first god card
        handled = choice_window_sprite.handle_click(self.game, click_pos)
        self.assertTrue(handled, "Click should be handled")
        self.assertIn(0, window.selected_indices, "God should be selected")
        
        # Window should still be open (waiting for confirm)
        self.assertIsNotNone(self.game.choice_window_manager.active_window,
                            "Window should remain open until confirmed")
        
        # Now click confirm button
        choice_window_sprite.sync_from_logical()
        self.assertIsNotNone(choice_window_sprite._confirm_rect, "Should have confirm button")
        confirm_pos = choice_window_sprite._confirm_rect.center
        choice_window_sprite.handle_click(self.game, confirm_pos)
        
        # Now window should be closed
        self.assertIsNone(self.game.choice_window_manager.active_window,
                         "Window should close after confirming selection")
        
        # Verify selected god was added to worshipped gods
        self.assertEqual(len(self.game.gods.worshipped), 1, 
                        "Should have 1 worshipped god after selection")
        self.assertEqual(self.game.gods.worshipped[0].name, first_god.name,
                        f"{first_god.name} should be the worshipped god")

    def test_single_selection_auto_confirms(self):
        """With max_selections=1, selecting a god should still require confirm button."""
        window = self.game.choice_window_manager.active_window
        
        # Select first god
        first_god = window.items[0]
        
        # Find the choice window sprite and simulate click
        choice_window_sprite = None
        for sprite in self.game.renderer.sprite_groups['modal']:
            if hasattr(sprite, 'choice_window') and sprite.choice_window == window:
                choice_window_sprite = sprite
                break
        
        self.assertIsNotNone(choice_window_sprite, "Should find choice window sprite")
        choice_window_sprite.sync_from_logical()
        
        # Click first god card
        first_button_idx, first_button_rect = choice_window_sprite._item_button_rects[0]
        choice_window_sprite.handle_click(self.game, first_button_rect.center)
        
        # Window should still be open (waiting for confirm)
        self.assertIsNotNone(self.game.choice_window_manager.active_window,
                            "Window should remain open until confirm button clicked")
        self.assertTrue(window.can_confirm(), "Should be able to confirm with 1 selection")
        
        # Click confirm button
        choice_window_sprite.sync_from_logical()
        confirm_pos = choice_window_sprite._confirm_rect.center
        choice_window_sprite.handle_click(self.game, confirm_pos)
        
        # Now window should be closed
        self.assertIsNone(self.game.choice_window_manager.active_window,
                         "Window should close after confirm")
        
        # Verify the selected god was added
        self.assertEqual(len(self.game.gods.worshipped), 1,
                        "Should have exactly 1 worshipped god")
        self.assertEqual(self.game.gods.worshipped[0].name, first_god.name,
                        "Selected god should be worshipped")


if __name__ == '__main__':
    unittest.main()
