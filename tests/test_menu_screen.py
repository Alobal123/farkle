"""Tests for main menu screen."""
import unittest
import pygame
from farkle.ui.screens.menu_screen import MenuScreen
from farkle.ui.settings import WIDTH, HEIGHT


class TestMenuScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.SysFont("Arial", 26)

    def setUp(self):
        self.menu = MenuScreen(self.screen, self.font)

    def test_menu_initialization(self):
        """Menu should initialize without errors."""
        self.assertFalse(self.menu.is_done())
        self.assertIsNone(self.menu.next_screen())
        self.assertFalse(self.menu.hovering)

    def test_menu_hover_detection(self):
        """Menu should detect hover over New Game button."""
        # Move mouse over button
        center_x, center_y = self.menu.new_game_button.center
        event = pygame.event.Event(pygame.MOUSEMOTION, {'pos': (center_x, center_y)})
        self.menu.handle_event(event)
        self.assertTrue(self.menu.hovering)

        # Move mouse away
        event = pygame.event.Event(pygame.MOUSEMOTION, {'pos': (0, 0)})
        self.menu.handle_event(event)
        self.assertFalse(self.menu.hovering)

    def test_menu_new_game_click(self):
        """Clicking New Game should transition to game screen."""
        # Click on New Game button
        center_x, center_y = self.menu.new_game_button.center
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
            'button': 1,
            'pos': (center_x, center_y)
        })
        self.menu.handle_event(event)
        
        self.assertTrue(self.menu.is_done())
        self.assertEqual(self.menu.next_screen(), 'game')

    def test_menu_draw_no_crash(self):
        """Menu draw should not crash."""
        try:
            self.menu.draw(self.screen)
        except Exception as e:
            self.fail(f"Menu draw crashed: {e}")


if __name__ == '__main__':
    unittest.main()
