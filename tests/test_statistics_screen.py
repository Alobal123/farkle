"""Tests for statistics screen."""
import unittest
import pygame
from farkle.ui.screens.statistics_screen import StatisticsScreen
from farkle.meta.persistence import PersistentStats
from farkle.ui.settings import WIDTH, HEIGHT


class TestStatisticsScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.SysFont("Arial", 26)

    def setUp(self):
        # Create sample statistics
        self.stats = PersistentStats()
        self.stats.total_games_played = 10
        self.stats.total_games_won = 6
        self.stats.total_games_lost = 4
        self.stats.lifetime_gold_gained = 5000
        self.stats.lifetime_score = 25000
        self.stats.highest_game_score = 3500
        
        self.stats_screen = StatisticsScreen(self.screen, self.font, self.stats)

    def test_stats_screen_initialization(self):
        """Statistics screen should initialize without errors."""
        self.assertFalse(self.stats_screen.is_done())
        self.assertIsNone(self.stats_screen.next_screen())
        self.assertFalse(self.stats_screen.hovering)

    def test_stats_screen_hover_detection(self):
        """Statistics screen should detect hover over Back button."""
        # Move mouse over button
        center_x, center_y = self.stats_screen.back_button.center
        event = pygame.event.Event(pygame.MOUSEMOTION, {'pos': (center_x, center_y)})
        self.stats_screen.handle_event(event)
        self.assertTrue(self.stats_screen.hovering)

        # Move mouse away
        event = pygame.event.Event(pygame.MOUSEMOTION, {'pos': (0, 0)})
        self.stats_screen.handle_event(event)
        self.assertFalse(self.stats_screen.hovering)

    def test_stats_screen_back_click(self):
        """Clicking Back should transition to menu screen."""
        # Click on Back button
        center_x, center_y = self.stats_screen.back_button.center
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
            'button': 1,
            'pos': (center_x, center_y)
        })
        self.stats_screen.handle_event(event)
        
        self.assertTrue(self.stats_screen.is_done())
        self.assertEqual(self.stats_screen.next_screen(), 'menu')
    
    def test_stats_screen_escape_key(self):
        """Pressing ESC should transition to menu screen."""
        event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        self.stats_screen.handle_event(event)
        
        self.assertTrue(self.stats_screen.is_done())
        self.assertEqual(self.stats_screen.next_screen(), 'menu')

    def test_stats_screen_draw_no_crash(self):
        """Statistics screen draw should not crash."""
        try:
            self.stats_screen.draw(self.screen)
        except Exception as e:
            self.fail(f"Statistics screen draw crashed: {e}")
    
    def test_stats_screen_with_empty_stats(self):
        """Statistics screen should handle empty stats gracefully."""
        empty_stats = PersistentStats()
        screen = StatisticsScreen(self.screen, self.font, empty_stats)
        
        try:
            screen.draw(self.screen)
        except Exception as e:
            self.fail(f"Drawing empty stats crashed: {e}")


if __name__ == '__main__':
    unittest.main()
