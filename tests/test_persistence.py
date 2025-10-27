"""Tests for persistent statistics storage."""
import unittest
import tempfile
import json
from pathlib import Path
from farkle.meta.persistence import PersistentStats, PersistenceManager


class PersistentStatsTests(unittest.TestCase):
    """Test PersistentStats merging and serialization."""
    
    def test_initial_state(self):
        """New PersistentStats should have all zeros."""
        stats = PersistentStats()
        self.assertEqual(stats.total_games_played, 0)
        self.assertEqual(stats.total_games_won, 0)
        self.assertEqual(stats.total_games_lost, 0)
        self.assertEqual(stats.lifetime_gold_gained, 0)
        self.assertEqual(stats.highest_game_score, 0)
    
    def test_merge_losing_session(self):
        """Merging a losing session should update counts and totals."""
        stats = PersistentStats()
        session = {
            'gold': {'total': 100},
            'farkles': {'total': 3},
            'scoring': {'total_score': 500, 'highest_single': 150},
            'gameplay': {
                'turns_played': 5,
                'dice_rolled': 30,
                'relics_purchased': 2,
                'goals_completed': 1,
                'levels_completed': 1
            }
        }
        
        stats.merge_session(session, success=False, level_index=2)
        
        self.assertEqual(stats.total_games_played, 1)
        self.assertEqual(stats.total_games_won, 0)
        self.assertEqual(stats.total_games_lost, 1)
        self.assertEqual(stats.lifetime_gold_gained, 100)
        self.assertEqual(stats.lifetime_farkles, 3)
        self.assertEqual(stats.lifetime_score, 500)
        self.assertEqual(stats.lifetime_turns_played, 5)
        self.assertEqual(stats.highest_single_score, 150)
        self.assertEqual(stats.highest_game_score, 500)
        self.assertEqual(stats.furthest_level_reached, 2)
    
    def test_merge_winning_session(self):
        """Merging a winning session should increment win count."""
        stats = PersistentStats()
        session = {
            'gold': {'total': 200},
            'farkles': {'total': 0},
            'scoring': {'total_score': 1000, 'highest_single': 300},
            'gameplay': {
                'turns_played': 10,
                'dice_rolled': 60,
                'relics_purchased': 5,
                'goals_completed': 3,
                'levels_completed': 3
            }
        }
        
        stats.merge_session(session, success=True, level_index=5)
        
        self.assertEqual(stats.total_games_played, 1)
        self.assertEqual(stats.total_games_won, 1)
        self.assertEqual(stats.total_games_lost, 0)
        self.assertEqual(stats.lifetime_gold_gained, 200)
    
    def test_merge_multiple_sessions(self):
        """Merging multiple sessions should accumulate correctly."""
        stats = PersistentStats()
        
        # First session
        session1 = {
            'gold': {'total': 100},
            'farkles': {'total': 2},
            'scoring': {'total_score': 500, 'highest_single': 150},
            'gameplay': {
                'turns_played': 5,
                'dice_rolled': 30,
                'relics_purchased': 2,
                'goals_completed': 1,
                'levels_completed': 1
            }
        }
        stats.merge_session(session1, success=False, level_index=2)
        
        # Second session
        session2 = {
            'gold': {'total': 150},
            'farkles': {'total': 1},
            'scoring': {'total_score': 800, 'highest_single': 200},
            'gameplay': {
                'turns_played': 8,
                'dice_rolled': 48,
                'relics_purchased': 3,
                'goals_completed': 2,
                'levels_completed': 2
            }
        }
        stats.merge_session(session2, success=True, level_index=3)
        
        # Check accumulated totals
        self.assertEqual(stats.total_games_played, 2)
        self.assertEqual(stats.total_games_won, 1)
        self.assertEqual(stats.total_games_lost, 1)
        self.assertEqual(stats.lifetime_gold_gained, 250)
        self.assertEqual(stats.lifetime_farkles, 3)
        self.assertEqual(stats.lifetime_score, 1300)
        self.assertEqual(stats.lifetime_turns_played, 13)
        self.assertEqual(stats.lifetime_dice_rolled, 78)
        
        # Check records (should be highest values)
        self.assertEqual(stats.highest_single_score, 200)
        self.assertEqual(stats.highest_game_score, 800)
        self.assertEqual(stats.furthest_level_reached, 3)
    
    def test_records_updated_correctly(self):
        """Records should only update when new values exceed old ones."""
        stats = PersistentStats()
        
        # First session with high scores
        session1 = {
            'gold': {'total': 500},
            'farkles': {'total': 0},
            'scoring': {'total_score': 2000, 'highest_single': 400},
            'gameplay': {
                'turns_played': 20,
                'dice_rolled': 120,
                'relics_purchased': 10,
                'goals_completed': 5,
                'levels_completed': 5
            }
        }
        stats.merge_session(session1, success=True, level_index=10)
        
        # Second session with lower scores
        session2 = {
            'gold': {'total': 100},
            'farkles': {'total': 5},
            'scoring': {'total_score': 500, 'highest_single': 150},
            'gameplay': {
                'turns_played': 5,
                'dice_rolled': 30,
                'relics_purchased': 2,
                'goals_completed': 1,
                'levels_completed': 1
            }
        }
        stats.merge_session(session2, success=False, level_index=3)
        
        # Records should still be from first session
        self.assertEqual(stats.highest_single_score, 400)
        self.assertEqual(stats.highest_game_score, 2000)
        self.assertEqual(stats.most_gold_in_game, 500)
        self.assertEqual(stats.most_turns_survived, 20)
        self.assertEqual(stats.furthest_level_reached, 10)
        
        # But totals should accumulate
        self.assertEqual(stats.total_games_played, 2)
        self.assertEqual(stats.lifetime_score, 2500)
    
    def test_serialization_roundtrip(self):
        """to_dict and from_dict should preserve all data."""
        stats = PersistentStats()
        stats.total_games_played = 10
        stats.lifetime_gold_gained = 5000
        stats.highest_game_score = 3000
        stats.unlocked_achievements = ['first_win', 'gold_hoarder']
        
        # Serialize and deserialize
        data = stats.to_dict()
        restored = PersistentStats.from_dict(data)
        
        self.assertEqual(restored.total_games_played, 10)
        self.assertEqual(restored.lifetime_gold_gained, 5000)
        self.assertEqual(restored.highest_game_score, 3000)
        self.assertEqual(restored.unlocked_achievements, ['first_win', 'gold_hoarder'])
    
    def test_from_dict_missing_fields(self):
        """from_dict should handle missing fields gracefully."""
        # Simulate old save file with missing fields
        data = {
            'total_games_played': 5,
            'lifetime_gold_gained': 1000
            # Missing many fields
        }
        
        stats = PersistentStats.from_dict(data)
        
        self.assertEqual(stats.total_games_played, 5)
        self.assertEqual(stats.lifetime_gold_gained, 1000)
        self.assertEqual(stats.lifetime_farkles, 0)  # Default value
        self.assertEqual(stats.unlocked_achievements, [])  # Default value


class PersistenceManagerTests(unittest.TestCase):
    """Test PersistenceManager file operations."""
    
    def test_new_file_creates_empty_stats(self):
        """Loading from non-existent file should create empty stats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / 'test_stats.json'
            manager = PersistenceManager(str(save_path))
            
            stats = manager.get_stats()
            self.assertEqual(stats.total_games_played, 0)
    
    def test_save_and_load(self):
        """Saving and loading should preserve all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / 'test_stats.json'
            
            # Create manager and modify stats
            manager1 = PersistenceManager(str(save_path))
            manager1.stats.total_games_played = 5
            manager1.stats.lifetime_gold_gained = 1000
            manager1.save()
            
            # Load in new manager instance
            manager2 = PersistenceManager(str(save_path))
            stats = manager2.get_stats()
            
            self.assertEqual(stats.total_games_played, 5)
            self.assertEqual(stats.lifetime_gold_gained, 1000)
    
    def test_merge_and_save(self):
        """merge_and_save should update stats and persist to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / 'test_stats.json'
            manager = PersistenceManager(str(save_path))
            
            session = {
                'gold': {'total': 100},
                'farkles': {'total': 2},
                'scoring': {'total_score': 500, 'highest_single': 150},
                'gameplay': {
                    'turns_played': 5,
                    'dice_rolled': 30,
                    'relics_purchased': 2,
                    'goals_completed': 1,
                    'levels_completed': 1
                }
            }
            
            manager.merge_and_save(session, success=False, level_index=2)
            
            # Verify file exists and contains correct data
            self.assertTrue(save_path.exists())
            
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertEqual(data['total_games_played'], 1)
            self.assertEqual(data['total_games_lost'], 1)
            self.assertEqual(data['lifetime_gold_gained'], 100)
    
    def test_reset(self):
        """Reset should clear all stats and save empty state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / 'test_stats.json'
            manager = PersistenceManager(str(save_path))
            
            # Add some data
            manager.stats.total_games_played = 10
            manager.save()
            
            # Reset
            manager.reset()
            
            # Verify reset worked
            self.assertEqual(manager.stats.total_games_played, 0)
            
            # Verify file was updated
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertEqual(data['total_games_played'], 0)
    
    def test_corrupted_file_creates_new_stats(self):
        """Loading corrupted JSON should create new stats instead of crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / 'test_stats.json'
            
            # Write corrupted JSON
            with open(save_path, 'w') as f:
                f.write("{ invalid json }")
            
            # Should not crash, should return empty stats
            manager = PersistenceManager(str(save_path))
            stats = manager.get_stats()
            self.assertEqual(stats.total_games_played, 0)


if __name__ == '__main__':
    unittest.main()
