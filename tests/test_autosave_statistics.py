"""Tests for statistics persistence in autosave system."""
import unittest
import pygame
import tempfile
from pathlib import Path

from farkle.game import Game
from farkle.meta.save_manager import SaveManager
from farkle.meta.statistics_tracker import GameStatistics
from farkle.ui.settings import WIDTH, HEIGHT


class AutosaveStatisticsTests(unittest.TestCase):
    """Test that statistics are properly saved and restored."""
    
    @classmethod
    def setUpClass(cls):
        """Set up pygame for all tests."""
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()
    
    def setUp(self):
        """Set up a fresh game and temporary save file for each test."""
        # Use temporary file for saves
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = Path(self.temp_dir) / 'test_save.json'
        
        # Create game with save manager
        self.game = Game(self.screen, self.font, self.clock, rng_seed=42)
        self.save_manager = SaveManager(str(self.save_path))
        self.save_manager.attach(self.game)
    
    def tearDown(self):
        """Clean up temporary files."""
        if self.save_path.exists():
            self.save_path.unlink()
        Path(self.temp_dir).rmdir()
    
    def test_statistics_saved_and_restored(self):
        """Test that statistics are included in save data and properly restored."""
        # Manually add some statistics (don't try to play since game needs initialization)
        stats = self.game.statistics_tracker.current_session
        stats.dice_rolled = 15
        stats.relics_purchased = 3
        stats.goals_completed = 2
        stats.levels_completed = 1
        stats.total_gold_gained = 500
        stats.total_faith_gained = 10
        stats.total_farkles = 5
        stats.turns_played = 10
        
        # Save the game
        self.assertTrue(self.save_manager.save())
        
        # Load save data
        save_data = self.save_manager.load()
        self.assertIsNotNone(save_data)
        
        # Verify statistics are in save data
        self.assertIn('statistics', save_data)
        stats_data = save_data['statistics']
        
        self.assertEqual(stats_data['relics_purchased'], 3)
        self.assertEqual(stats_data['goals_completed'], 2)
        self.assertEqual(stats_data['levels_completed'], 1)
        self.assertEqual(stats_data['total_gold_gained'], 500)
        self.assertEqual(stats_data['total_faith_gained'], 10)
        self.assertEqual(stats_data['total_farkles'], 5)
        self.assertEqual(stats_data['turns_played'], 10)
        self.assertGreater(stats_data['dice_rolled'], 0)  # Should have rolled some dice
    
    def test_statistics_restored_to_new_game(self):
        """Test that statistics are correctly restored when loading a save."""
        # Set up initial statistics
        stats = self.game.statistics_tracker.current_session
        stats.relics_purchased = 5
        stats.goals_completed = 3
        stats.total_score = 1000
        stats.highest_single_score = 300
        
        # Save the game
        self.save_manager.save()
        save_data = self.save_manager.load()
        
        # Create a new game (simulating app restart)
        new_game = Game(self.screen, self.font, self.clock, rng_seed=42)
        
        # Restore the save
        self.save_manager.game = new_game
        self.assertTrue(self.save_manager.restore_game_state(new_game, save_data))
        
        # Verify statistics were restored
        restored_stats = new_game.statistics_tracker.current_session
        self.assertEqual(restored_stats.relics_purchased, 5)
        self.assertEqual(restored_stats.goals_completed, 3)
        self.assertEqual(restored_stats.total_score, 1000)
        self.assertEqual(restored_stats.highest_single_score, 300)
    
    def test_statistics_events_preserved(self):
        """Test that event history is preserved in statistics."""
        # Add some events manually
        stats = self.game.statistics_tracker.current_session
        stats.gold_events = [{'amount': 100, 'source': 'goal', 'total_after': 100}, 
                             {'amount': 50, 'source': 'bonus', 'total_after': 150}]
        stats.farkle_events = [{'turn': 5, 'farkle_count': 1}]
        stats.score_events = [{'adjusted': 200, 'raw': 150, 'rule_key': 'test', 'total_after': 200}]
        
        # Save and reload
        self.save_manager.save()
        save_data = self.save_manager.load()
        
        new_game = Game(self.screen, self.font, self.clock, rng_seed=99)  # Different seed to avoid conflicts
        
        self.save_manager.game = new_game
        self.save_manager.restore_game_state(new_game, save_data)
        
        # Verify event lists were preserved
        restored_stats = new_game.statistics_tracker.current_session
        # Note: The lengths might be > expected if game initialization adds events,
        # so we check that our saved events are present at the beginning
        self.assertGreaterEqual(len(restored_stats.gold_events), 2)
        self.assertGreaterEqual(len(restored_stats.farkle_events), 1)
        self.assertGreaterEqual(len(restored_stats.score_events), 1)
        
        # Check the saved events are present
        self.assertEqual(restored_stats.gold_events[0]['amount'], 100)
        self.assertEqual(restored_stats.gold_events[1]['amount'], 50)
        self.assertEqual(restored_stats.farkle_events[0]['turn'], 5)
        self.assertEqual(restored_stats.score_events[0]['adjusted'], 200)


if __name__ == '__main__':
    unittest.main()
