"""Tests for Faith system integration."""
import unittest
import pygame
import tempfile
from pathlib import Path
from farkle.meta.persistence import PersistentStats, PersistenceManager
from farkle.meta.statistics_tracker import GameStatistics
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class FaithSystemTests(unittest.TestCase):
    """Test the Faith system end-to-end."""
    
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 36)
        cls.clock = pygame.time.Clock()
    
    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1)
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))
    
    def test_faith_tracked_in_statistics(self):
        """StatisticsTracker should track faith gained from events."""
        stats = GameStatistics()
        
        # Simulate 2 faith gain events
        event1 = GameEvent(GameEventType.FAITH_GAINED, payload={'amount': 2, 'goal_name': 'Priest 1'})
        event2 = GameEvent(GameEventType.FAITH_GAINED, payload={'amount': 2, 'goal_name': 'Priest 2'})
        
        stats.add_faith_event(event1)
        stats.add_faith_event(event2)
        
        summary = stats.get_summary()
        
        self.assertEqual(summary['faith']['total'], 4)
        self.assertEqual(summary['faith']['events_count'], 2)
    
    def test_faith_persists_across_sessions(self):
        """Faith should be saved to disk and loaded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / 'test_faith.json'
            
            # Create first manager and add faith
            manager1 = PersistenceManager(str(save_path))
            manager1.stats.faith = 10
            manager1.save()
            
            # Create second manager and verify faith loaded
            manager2 = PersistenceManager(str(save_path))
            self.assertEqual(manager2.stats.faith, 10)
    
    def test_faith_calculation_from_events(self):
        """Faith should be calculated from FAITH_GAINED events."""
        stats = PersistentStats()
        
        # Session with 3 faith events (6 total faith)
        session = {
            'gold': {'total': 100},
            'farkles': {'total': 0},
            'scoring': {'total_score': 600, 'highest_single': 200},
            'faith': {'total': 6, 'events_count': 3},
            'gameplay': {
                'turns_played': 5,
                'dice_rolled': 30,
                'relics_purchased': 2,
                'goals_completed': 5,
                'levels_completed': 1
            }
        }
        
        stats.merge_session(session, success=False, level_index=1)
        
        # Should have 6 faith from events
        self.assertEqual(stats.faith, 6)
    
    def test_faith_accumulates_not_replaces(self):
        """Faith should accumulate across sessions, not replace."""
        stats = PersistentStats()
        stats.faith = 5  # Starting faith
        
        # Session with 4 faith gained
        session = {
            'gold': {'total': 50},
            'farkles': {'total': 0},
            'scoring': {'total_score': 300, 'highest_single': 100},
            'faith': {'total': 4, 'events_count': 2},
            'gameplay': {
                'turns_played': 3,
                'dice_rolled': 18,
                'relics_purchased': 1,
                'goals_completed': 3,
                'levels_completed': 1
            }
        }
        
        stats.merge_session(session, success=False, level_index=1)
        
        # Should be 5 + 4 = 9
        self.assertEqual(stats.faith, 9)
    
    def test_no_faith_events_no_faith_gain(self):
        """Sessions without faith events should not grant faith."""
        stats = PersistentStats()
        
        session = {
            'gold': {'total': 50},
            'farkles': {'total': 0},
            'scoring': {'total_score': 300, 'highest_single': 100},
            'faith': {'total': 0, 'events_count': 0},
            'gameplay': {
                'turns_played': 3,
                'dice_rolled': 18,
                'relics_purchased': 1,
                'goals_completed': 2,
                'levels_completed': 1
            }
        }
        
        stats.merge_session(session, success=False, level_index=1)
        
        # Should remain 0
        self.assertEqual(stats.faith, 0)
    
    def test_faith_serialization_roundtrip(self):
        """Faith should survive serialization and deserialization."""
        stats = PersistentStats()
        stats.faith = 42
        
        # Serialize
        data = stats.to_dict()
        
        # Deserialize
        restored = PersistentStats.from_dict(data)
        
        self.assertEqual(restored.faith, 42)
    
    def test_player_gains_faith_from_priest_goal(self):
        """Player should gain faith when priest goal is fulfilled."""
        from farkle.goals.goal import Goal
        
        # Create a priest goal with faith reward
        priest_goal = Goal(
            target_score=100,
            game=self.game,
            name="Test Priest Petition",
            is_disaster=False,
            reward_faith=2,
            persona="priest"
        )
        priest_goal.activate(self.game)
        
        # Manually fulfill the goal
        priest_goal.remaining = 0
        initial_faith = self.game.player.faith
        
        # Trigger goal fulfilled event
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOAL_FULFILLED,
            payload={'goal': priest_goal}
        ))
        
        # Player should have gained faith
        self.assertGreater(self.game.player.faith, initial_faith)
        
        # Should have emitted FAITH_GAINED event
        faith_events = [e for e in self.events if e.type == GameEventType.FAITH_GAINED]
        self.assertGreater(len(faith_events), 0)


if __name__ == '__main__':
    unittest.main()
