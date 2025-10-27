"""Tests for game over screen and level failure handling."""
import unittest
import pygame
from farkle.ui.screens.game_over_screen import GameOverScreen
from farkle.ui.settings import WIDTH, HEIGHT


class TestGameOverScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.SysFont("Arial", 26)

    def test_game_over_screen_failure(self):
        """Test game over screen for failure."""
        screen = GameOverScreen(
            self.screen, 
            self.font,
            success=False,
            level_name="Test Level",
            level_index=3,
            unfinished_goals=["Avert the Plague", "Stop the Earthquake"]
        )
        
        self.assertFalse(screen.success)
        self.assertEqual(screen.level_name, "Test Level")
        self.assertEqual(screen.level_index, 3)
        self.assertFalse(screen.is_done())

    def test_game_over_screen_success(self):
        """Test game over screen for victory."""
        screen = GameOverScreen(
            self.screen, 
            self.font,
            success=True,
            level_name="Final Trial",
            level_index=10,
            unfinished_goals=[]
        )
        
        self.assertTrue(screen.success)
        self.assertEqual(screen.level_name, "Final Trial")
        self.assertEqual(screen.level_index, 10)

    def test_game_over_button_click(self):
        """Test clicking return to menu button."""
        screen = GameOverScreen(
            self.screen, 
            self.font,
            success=False,
            level_name="Test",
            level_index=1
        )
        
        # Simulate click on menu button
        center_x, center_y = screen.menu_button.center
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
            'button': 1,
            'pos': (center_x, center_y)
        })
        screen.handle_event(event)
        
        self.assertTrue(screen.is_done())
        self.assertEqual(screen.next_screen(), 'menu')

    def test_game_over_keyboard_shortcut(self):
        """Test keyboard shortcuts to return to menu."""
        screen = GameOverScreen(
            self.screen, 
            self.font,
            success=False,
            level_name="Test",
            level_index=1
        )
        
        # Test SPACE key
        event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_SPACE})
        screen.handle_event(event)
        
        self.assertTrue(screen.is_done())
        self.assertEqual(screen.next_screen(), 'menu')

    def test_game_over_draw_no_crash(self):
        """Test that drawing doesn't crash."""
        screen = GameOverScreen(
            self.screen, 
            self.font,
            success=False,
            level_name="Test",
            level_index=1,
            unfinished_goals=["Goal 1", "Goal 2"]
        )
        
        try:
            screen.draw(self.screen)
        except Exception as e:
            self.fail(f"Game over screen draw crashed: {e}")


if __name__ == '__main__':
    unittest.main()
