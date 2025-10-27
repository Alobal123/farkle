"""Test autosave functionality."""
import unittest
import pygame
import tempfile
import json
from pathlib import Path
from farkle.game import Game
from farkle.meta.save_manager import SaveManager
from farkle.core.game_event import GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class AutosaveTests(unittest.TestCase):
    """Test autosave and load functionality."""
    
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()
    
    def setUp(self):
        # Create temporary save file path for testing
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = Path(self.temp_dir) / 'test_save.json'
        self.save_manager = SaveManager(save_path=str(self.save_path))
        
        # Create game with seeded RNG for determinism
        self.game = Game(self.screen, self.font, self.clock, rng_seed=42)
        self.save_manager.attach(self.game)
    
    def tearDown(self):
        # Clean up temp file
        if self.save_path.exists():
            self.save_path.unlink()
    
    def test_save_creates_file(self):
        """Test that saving creates a file."""
        self.assertFalse(self.save_path.exists())
        
        success = self.save_manager.save()
        
        self.assertTrue(success)
        self.assertTrue(self.save_path.exists())
    
    def test_save_contains_player_data(self):
        """Test that save file contains player state."""
        # Modify player state
        self.game.player.gold = 150
        self.game.player.faith = 25
        self.game.player.temple_income = 50
        
        self.save_manager.save()
        
        # Read save file
        with open(self.save_path, 'r') as f:
            save_data = json.load(f)
        
        self.assertEqual(save_data['player']['gold'], 150)
        self.assertEqual(save_data['player']['faith'], 25)
        self.assertEqual(save_data['player']['temple_income'], 50)
    
    def test_save_contains_level_data(self):
        """Test that save file contains level state."""
        # Modify level state
        if self.game.level_state:
            self.game.level_state.turns_left = 2
        self.game.level_index = 3
        
        self.save_manager.save()
        
        # Read save file
        with open(self.save_path, 'r') as f:
            save_data = json.load(f)
        
        self.assertEqual(save_data['level']['turns_left'], 2)
        self.assertEqual(save_data['level']['level_index'], 3)
    
    def test_save_contains_goals(self):
        """Test that save file contains goal progress."""
        # Modify first goal's progress
        if self.game.level_state and self.game.level_state.goals:
            goal = self.game.level_state.goals[0]
            goal.remaining = 100
            goal.pending_raw = 50
        
        self.save_manager.save()
        
        # Read save file
        with open(self.save_path, 'r') as f:
            save_data = json.load(f)
        
        goals = save_data['level']['goals']
        self.assertGreater(len(goals), 0)
        self.assertEqual(goals[0]['remaining'], 100)
        self.assertEqual(goals[0]['pending_raw'], 50)
    
    def test_autosave_on_turn_end(self):
        """Test that game autosaves on TURN_END event."""
        self.assertFalse(self.save_path.exists())
        
        # Simulate TURN_END event
        from farkle.core.game_event import GameEvent
        event = GameEvent(GameEventType.TURN_END, {})
        self.save_manager.on_event(event)
        
        self.assertTrue(self.save_path.exists())
    
    def test_autosave_on_shop_closed(self):
        """Test that game autosaves on SHOP_CLOSED event."""
        self.assertFalse(self.save_path.exists())
        
        # Simulate SHOP_CLOSED event
        from farkle.core.game_event import GameEvent
        event = GameEvent(GameEventType.SHOP_CLOSED, {})
        self.save_manager.on_event(event)
        
        self.assertTrue(self.save_path.exists())
    
    def test_load_restores_player_state(self):
        """Test that loading restores player state."""
        # Save game with modified player state
        self.game.player.gold = 200
        self.game.player.faith = 30
        self.save_manager.save()
        
        # Create new game and load save
        new_game = Game(self.screen, self.font, self.clock, rng_seed=1)
        save_data = self.save_manager.load()
        self.assertIsNotNone(save_data)
        
        success = self.save_manager.restore_game_state(new_game, save_data)
        
        self.assertTrue(success)
        self.assertEqual(new_game.player.gold, 200)
        self.assertEqual(new_game.player.faith, 30)
    
    def test_load_restores_level_state(self):
        """Test that loading restores level state."""
        # Save game with modified level state
        if self.game.level_state:
            self.game.level_state.turns_left = 1
        self.game.level_index = 5
        self.save_manager.save()
        
        # Create new game and load save
        new_game = Game(self.screen, self.font, self.clock, rng_seed=1)
        save_data = self.save_manager.load()
        
        self.save_manager.restore_game_state(new_game, save_data)
        
        if new_game.level_state:
            self.assertEqual(new_game.level_state.turns_left, 1)
        self.assertEqual(new_game.level_index, 5)
    
    def test_load_restores_goal_progress(self):
        """Test that loading restores goal progress."""
        # Save game with modified goal progress
        if self.game.level_state and self.game.level_state.goals:
            goal = self.game.level_state.goals[0]
            goal.remaining = 75
            goal.pending_raw = 25
        self.save_manager.save()
        
        # Create new game and load save
        new_game = Game(self.screen, self.font, self.clock, rng_seed=1)
        save_data = self.save_manager.load()
        
        self.save_manager.restore_game_state(new_game, save_data)
        
        if new_game.level_state and new_game.level_state.goals:
            restored_goal = new_game.level_state.goals[0]
            self.assertEqual(restored_goal.remaining, 75)
            self.assertEqual(restored_goal.pending_raw, 25)
    
    def test_has_save_returns_true_when_file_exists(self):
        """Test has_save() returns True when save file exists."""
        self.assertFalse(self.save_manager.has_save())
        
        self.save_manager.save()
        
        self.assertTrue(self.save_manager.has_save())
    
    def test_delete_save_removes_file(self):
        """Test delete_save() removes save file."""
        self.save_manager.save()
        self.assertTrue(self.save_path.exists())
        
        success = self.save_manager.delete_save()
        
        self.assertTrue(success)
        self.assertFalse(self.save_path.exists())
    
    def test_load_nonexistent_save_returns_none(self):
        """Test loading when no save exists returns None."""
        self.assertFalse(self.save_path.exists())
        
        save_data = self.save_manager.load()
        
        self.assertIsNone(save_data)
    
    def test_save_version_included(self):
        """Test that save file includes version number."""
        self.save_manager.save()
        
        with open(self.save_path, 'r') as f:
            save_data = json.load(f)
        
        self.assertIn('version', save_data)
        self.assertEqual(save_data['version'], '1.0')
    
    def test_save_contains_active_effects(self):
        """Test that save file contains active effects (blessings/curses)."""
        from farkle.blessings import DoubleScoreBlessing
        
        # Add a blessing to the player
        blessing = DoubleScoreBlessing(duration=2)
        self.game.player.active_effects.append(blessing)
        blessing.player = self.game.player
        
        self.save_manager.save()
        
        # Read save file
        with open(self.save_path, 'r') as f:
            save_data = json.load(f)
        
        effects = save_data['player']['active_effects']
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]['type'], 'DoubleScoreBlessing')
        self.assertEqual(effects[0]['name'], 'Divine Fortune')
        self.assertEqual(effects[0]['duration'], 2)
    
    def test_load_restores_active_effects(self):
        """Test that loading restores active effects (blessings)."""
        from farkle.blessings import DoubleScoreBlessing
        
        # Add a blessing and save
        blessing = DoubleScoreBlessing(duration=3)
        self.game.player.active_effects.append(blessing)
        blessing.player = self.game.player
        blessing.activate(self.game)
        
        self.save_manager.save()
        
        # Create new game and load
        new_game = Game(self.screen, self.font, self.clock, rng_seed=1)
        self.assertEqual(len(new_game.player.active_effects), 0)
        
        save_data = self.save_manager.load()
        self.save_manager.restore_game_state(new_game, save_data)
        
        # Verify blessing restored
        self.assertEqual(len(new_game.player.active_effects), 1)
        restored_effect = new_game.player.active_effects[0]
        self.assertEqual(restored_effect.name, 'Divine Fortune')
        self.assertEqual(restored_effect.duration, 3)
        self.assertTrue(restored_effect.active)
    
    def test_load_restores_goal_target_scores(self):
        """Test that loading restores goal target scores to prevent negative values."""
        # Modify goal progress
        if self.game.level_state and self.game.level_state.goals:
            goal = self.game.level_state.goals[0]
            original_target = goal.target_score
            original_name = goal.name
            
            # Partially complete the goal
            goal.remaining = original_target - 150
            goal.pending_raw = 25
        
        self.save_manager.save()
        
        # Create new game (will generate different random goals)
        new_game = Game(self.screen, self.font, self.clock, rng_seed=999)
        
        # Load saved data
        save_data = self.save_manager.load()
        self.save_manager.restore_game_state(new_game, save_data)
        
        # Verify goal was properly restored
        if new_game.level_state and new_game.level_state.goals:
            restored_goal = new_game.level_state.goals[0]
            
            # Target score should match saved value
            self.assertEqual(restored_goal.target_score, original_target)
            # Name should match saved value
            self.assertEqual(restored_goal.name, original_name)
            # Remaining should be positive and match saved value
            self.assertEqual(restored_goal.remaining, original_target - 150)
            self.assertGreaterEqual(restored_goal.remaining, 0, 
                                  "Goal remaining should not be negative after restore")
            # Pending should match
            self.assertEqual(restored_goal.pending_raw, 25)


if __name__ == '__main__':
    unittest.main()
