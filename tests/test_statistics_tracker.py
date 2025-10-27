"""Test statistics tracker for meta progression."""
import unittest
import pygame
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class StatisticsTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1)
        # Reset statistics after game initialization to have clean baseline
        self.game.statistics_tracker.reset()

    def test_statistics_tracker_exists(self):
        """Statistics tracker should be initialized with the game."""
        self.assertIsNotNone(self.game.statistics_tracker)
        
    def test_gold_tracking(self):
        """Statistics tracker should record gold gained events."""
        # Emit a gold gained event
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOLD_GAINED,
            payload={'amount': 100, 'source': 'test'}
        ))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.total_gold_gained, 100)
        self.assertEqual(len(stats.gold_events), 1)
        self.assertEqual(stats.gold_events[0]['amount'], 100)
        self.assertEqual(stats.gold_events[0]['source'], 'test')
        
    def test_multiple_gold_events(self):
        """Statistics tracker should accumulate multiple gold events."""
        # Emit multiple gold events
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOLD_GAINED,
            payload={'amount': 50, 'source': 'test1'}
        ))
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOLD_GAINED,
            payload={'amount': 75, 'source': 'test2'}
        ))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.total_gold_gained, 125)
        self.assertEqual(len(stats.gold_events), 2)
        
    def test_farkle_tracking(self):
        """Statistics tracker should record farkle events."""
        # Emit farkle events
        self.game.event_listener.publish(GameEvent(GameEventType.FARKLE))
        self.game.event_listener.publish(GameEvent(GameEventType.FARKLE))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.total_farkles, 2)
        self.assertEqual(len(stats.farkle_events), 2)
        
    def test_score_tracking(self):
        """Statistics tracker should record score applied events."""
        # Emit score events
        self.game.event_listener.publish(GameEvent(
            GameEventType.SCORE_APPLIED,
            payload={'adjusted': 100, 'raw': 50, 'rule_key': 'SingleValue:5'}
        ))
        self.game.event_listener.publish(GameEvent(
            GameEventType.SCORE_APPLIED,
            payload={'adjusted': 200, 'raw': 150, 'rule_key': 'ThreeOfAKind:1'}
        ))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.total_score, 300)
        self.assertEqual(stats.highest_single_score, 200)
        self.assertEqual(len(stats.score_events), 2)
        
    def test_turn_counting(self):
        """Statistics tracker should count turns."""
        # Emit turn end events (TURN_END is used instead of TURN_START to avoid counting initial setup)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END))
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.turns_played, 2)
        
    def test_dice_rolled_counting(self):
        """Statistics tracker should count dice rolled."""
        # Emit die rolled events (6 dice)
        for _ in range(6):
            self.game.event_listener.publish(GameEvent(GameEventType.DIE_ROLLED))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertGreaterEqual(stats.dice_rolled, 6)
        
    def test_relic_purchase_counting(self):
        """Statistics tracker should count relics purchased."""
        self.game.event_listener.publish(GameEvent(GameEventType.RELIC_PURCHASED))
        self.game.event_listener.publish(GameEvent(GameEventType.RELIC_PURCHASED))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.relics_purchased, 2)
        
    def test_goal_completion_counting(self):
        """Statistics tracker should count goals completed."""
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.goals_completed, 1)
        
    def test_level_completion_counting(self):
        """Statistics tracker should count levels completed."""
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_COMPLETE))
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.levels_completed, 1)
        
    def test_export_summary(self):
        """Statistics tracker should export a summary."""
        # Add some events
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOLD_GAINED,
            payload={'amount': 100, 'source': 'test'}
        ))
        self.game.event_listener.publish(GameEvent(GameEventType.FARKLE))
        self.game.event_listener.publish(GameEvent(
            GameEventType.SCORE_APPLIED,
            payload={'adjusted': 150, 'raw': 100, 'rule_key': 'test'}
        ))
        
        summary = self.game.statistics_tracker.export_summary()
        
        # Verify summary structure
        self.assertIn('gold', summary)
        self.assertIn('farkles', summary)
        self.assertIn('scoring', summary)
        self.assertIn('gameplay', summary)
        
        # Verify values
        self.assertEqual(summary['gold']['total'], 100)
        self.assertEqual(summary['farkles']['total'], 1)
        self.assertEqual(summary['scoring']['total_score'], 150)
        
    def test_reset_statistics(self):
        """Statistics tracker should reset for new game."""
        # Add some events
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOLD_GAINED,
            payload={'amount': 100, 'source': 'test'}
        ))
        
        # Reset
        self.game.statistics_tracker.reset()
        
        stats = self.game.statistics_tracker.get_statistics()
        self.assertEqual(stats.total_gold_gained, 0)
        self.assertEqual(len(stats.gold_events), 0)


if __name__ == '__main__':
    unittest.main()
