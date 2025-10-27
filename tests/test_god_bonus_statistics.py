"""Test that god level 3 reward bonuses are tracked in statistics."""
import unittest
import pygame
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class GodBonusStatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=42)

    def test_god_bonus_gold_tracked_separately(self):
        """Test that god bonus gold is tracked with source='god_bonus'."""
        from farkle.gods.demeter import Demeter
        from farkle.goals.goal import Goal
        
        # Set up Demeter at level 3
        demeter = Demeter(self.game)
        demeter.level = 3
        demeter.activate(self.game)
        
        # Clear any existing gold events from game setup (temple income)
        self.game.statistics_tracker.current_session.gold_events.clear()
        self.game.statistics_tracker.current_session.total_gold_gained = 0
        
        # Create a nature goal with gold reward
        goal = Goal(100, self.game, "Test Nature Goal", category="nature", 
                   reward_gold=100, is_disaster=True)
        
        # Mark goal as fulfilled
        goal.remaining = 0
        
        # Fulfill the goal (will emit GOLD_REWARDED -> GOLD_GAINED -> god bonus)
        goal.claim_reward()
        
        # Check statistics
        stats = self.game.statistics_tracker.get_statistics()
        
        # Should have 2 gold events: one from goal, one from god bonus
        self.assertEqual(len(stats.gold_events), 2, "Should have 2 gold events")
        
        # First event should be from goal
        self.assertEqual(stats.gold_events[0]['source'], 'goal_reward')
        self.assertEqual(stats.gold_events[0]['amount'], 100)
        self.assertEqual(stats.gold_events[0]['goal_category'], 'nature')
        
        # Second event should be from god bonus
        self.assertEqual(stats.gold_events[1]['source'], 'god_bonus')
        self.assertEqual(stats.gold_events[1]['amount'], 100)
        self.assertEqual(stats.gold_events[1]['god_name'], 'Demeter')
        
        # Total should be doubled
        self.assertEqual(stats.total_gold_gained, 200)

    def test_god_bonus_faith_tracked_separately(self):
        """Test that god bonus faith is tracked with source='god_bonus'."""
        from farkle.gods.hades import Hades
        from farkle.goals.goal import Goal
        
        # Set up Hades at level 3
        hades = Hades(self.game)
        hades.level = 3
        hades.activate(self.game)
        
        # Create a spirit goal with faith reward
        goal = Goal(100, self.game, "Test Spirit Goal", category="spirit", 
                   reward_faith=50, is_disaster=True)
        
        # Mark goal as fulfilled
        goal.remaining = 0
        
        # Fulfill the goal
        goal.claim_reward()
        
        # Check statistics
        stats = self.game.statistics_tracker.get_statistics()
        
        # Should have 2 faith events
        self.assertEqual(len(stats.faith_events), 2, "Should have 2 faith events")
        
        # First event should be from goal
        self.assertEqual(stats.faith_events[0]['source'], 'goal_reward')
        self.assertEqual(stats.faith_events[0]['amount'], 50)
        
        # Second event should be from god bonus
        self.assertEqual(stats.faith_events[1]['source'], 'god_bonus')
        self.assertEqual(stats.faith_events[1]['amount'], 50)
        self.assertEqual(stats.faith_events[1]['god_name'], 'Hades')
        
        # Total should be doubled
        self.assertEqual(stats.total_faith_gained, 100)

    def test_non_matching_category_no_bonus(self):
        """Test that gods don't give bonuses for non-matching categories."""
        from farkle.gods.demeter import Demeter
        from farkle.goals.goal import Goal
        
        # Set up Demeter at level 3
        demeter = Demeter(self.game)
        demeter.level = 3
        demeter.activate(self.game)
        
        # Clear any existing gold events from game setup
        self.game.statistics_tracker.current_session.gold_events.clear()
        self.game.statistics_tracker.current_session.total_gold_gained = 0
        
        # Create a warfare goal (not nature)
        goal = Goal(100, self.game, "Test Warfare Goal", category="warfare", 
                   reward_gold=100, is_disaster=True)
        
        # Mark goal as fulfilled
        goal.remaining = 0
        
        # Fulfill the goal
        goal.claim_reward()
        
        # Check statistics
        stats = self.game.statistics_tracker.get_statistics()
        
        # Should have only 1 gold event (no god bonus)
        self.assertEqual(len(stats.gold_events), 1, "Should have only 1 gold event")
        self.assertEqual(stats.gold_events[0]['source'], 'goal_reward')
        self.assertEqual(stats.total_gold_gained, 100)

    def test_god_level_2_no_bonus(self):
        """Test that gods at level 2 don't give reward bonuses."""
        from farkle.gods.ares import Ares
        from farkle.goals.goal import Goal
        
        # Set up Ares at level 2 (not level 3)
        ares = Ares(self.game)
        ares.level = 2
        ares.activate(self.game)
        
        # Clear any existing gold events from game setup
        self.game.statistics_tracker.current_session.gold_events.clear()
        self.game.statistics_tracker.current_session.total_gold_gained = 0
        
        # Create a warfare goal
        goal = Goal(100, self.game, "Test Warfare Goal", category="warfare", 
                   reward_gold=100, is_disaster=True)
        
        # Mark goal as fulfilled
        goal.remaining = 0
        
        # Fulfill the goal
        goal.claim_reward()
        
        # Check statistics
        stats = self.game.statistics_tracker.get_statistics()
        
        # Should have only 1 gold event (no god bonus at level 2)
        self.assertEqual(len(stats.gold_events), 1, "Should have only 1 gold event")
        self.assertEqual(stats.total_gold_gained, 100)


if __name__ == '__main__':
    unittest.main()
