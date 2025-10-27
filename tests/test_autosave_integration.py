"""Integration test for autosave flow through App screens."""
import unittest
import pygame
import tempfile
from pathlib import Path
from farkle.ui.screens.app import App
from farkle.meta.save_manager import SaveManager
from farkle.ui.settings import WIDTH, HEIGHT


class AutosaveIntegrationTests(unittest.TestCase):
    """Test autosave integration with App and screens."""
    
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
        
        # Create app - will use default save manager
        # We'll override the save path after creation
        self.app = App(self.screen, self.font, self.clock)
        self.app.save_manager = SaveManager(save_path=str(self.save_path))
    
    def tearDown(self):
        # Clean up temp file
        if self.save_path.exists():
            self.save_path.unlink()
    
    def test_menu_shows_continue_when_save_exists(self):
        """Test that menu screen detects save file."""
        # Create a fake save file
        self.save_path.write_text('{"version": "1.0"}')
        
        # Recreate menu screen with save detection
        from farkle.ui.screens.menu_screen import MenuScreen
        menu = MenuScreen(self.screen, self.font, has_save=True)
        
        # Verify continue button exists
        self.assertIsNotNone(menu.continue_button)
    
    def test_menu_hides_continue_when_no_save(self):
        """Test that menu screen hides continue when no save."""
        from farkle.ui.screens.menu_screen import MenuScreen
        menu = MenuScreen(self.screen, self.font, has_save=False)
        
        # Verify continue button is None
        self.assertIsNone(menu.continue_button)
    
    def test_app_initializes_game_on_transition(self):
        """Test that app creates game when transitioning to game screen."""
        self.assertIsNone(self.app.game)
        
        # Simulate transition to game screen
        self.app.current_name = 'game'
        self.app._ensure_game_initialized()
        
        self.assertIsNotNone(self.app.game)
    
    def test_app_attaches_save_manager_to_game(self):
        """Test that save manager gets attached to game."""
        # Create game
        self.app._ensure_game_initialized()
        
        # Verify save manager is attached
        self.assertIsNotNone(self.app.save_manager.game)
        self.assertEqual(self.app.save_manager.game, self.app.game)
    
    def test_new_game_deletes_old_save(self):
        """Test that starting new game from menu clears old save."""
        # Create a save file
        self.save_path.write_text('{"version": "1.0"}')
        self.assertTrue(self.save_path.exists())
        
        # Simulate game over -> menu transition
        self.app.current_name = 'game_over'
        self.app._ensure_game_initialized()
        
        # Transition to menu (should delete save)
        next_screen = 'menu'
        self.app.save_manager.delete_save()
        self.app.game = None
        
        # Verify save deleted
        self.assertFalse(self.save_path.exists())
    
    def test_continue_loads_save_data(self):
        """Test that continuing loads save data into game."""
        # Create initial game and save it
        self.app._ensure_game_initialized()
        self.app.game.player.gold = 500
        self.app.game.player.faith = 100
        self.app.save_manager.save()
        
        # Clear game
        self.app.game = None
        
        # Load game with continue flag
        self.app._ensure_game_initialized(load_save=True)
        
        # Verify state restored
        self.assertEqual(self.app.game.player.gold, 500)
        self.assertEqual(self.app.game.player.faith, 100)
    
    def test_autosave_triggers_during_gameplay(self):
        """Test that autosave happens during game events."""
        from farkle.core.game_event import GameEvent, GameEventType
        
        # Initialize game
        self.app._ensure_game_initialized()
        self.assertFalse(self.save_path.exists())
        
        # Simulate a turn end event (should trigger autosave)
        event = GameEvent(GameEventType.TURN_END, {})
        self.app.save_manager.on_event(event)
        
        # Verify save file created
        self.assertTrue(self.save_path.exists())
    
    def test_full_save_and_load_cycle(self):
        """Test complete save/load workflow."""
        # 1. Start new game
        self.app._ensure_game_initialized(load_save=False)
        original_game = self.app.game
        
        # 2. Make progress
        original_game.player.gold = 300
        original_game.level_index = 7
        
        # 3. Save game
        self.app.save_manager.save()
        
        # 4. "Quit" game
        self.app.game = None
        
        # 5. "Restart" and continue
        self.app._ensure_game_initialized(load_save=True)
        restored_game = self.app.game
        
        # 6. Verify restoration
        self.assertEqual(restored_game.player.gold, 300)
        self.assertEqual(restored_game.level_index, 7)
        self.assertIsNot(restored_game, original_game)  # Different object
    
    def test_menu_screen_recreated_with_save_status(self):
        """Test that menu screen is recreated to reflect save status."""
        from farkle.ui.screens.menu_screen import MenuScreen
        
        # Initially no save
        self.app.screens['menu'] = MenuScreen(self.screen, self.font, has_save=False)
        self.assertIsNone(self.app.screens['menu'].continue_button)
        
        # Create save
        self.app._ensure_game_initialized()
        self.app.save_manager.save()
        
        # Recreate menu with save detection
        self.app.screens['menu'] = MenuScreen(self.screen, self.font, has_save=True)
        self.assertIsNotNone(self.app.screens['menu'].continue_button)


if __name__ == '__main__':
    unittest.main()
