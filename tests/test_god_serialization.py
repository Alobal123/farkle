"""Tests for god serialization and deserialization."""

import unittest
import tempfile
import pygame
from farkle.game import Game
from farkle.gods.ares import Ares
from farkle.gods.hermes import Hermes
from farkle.gods.hades import Hades
from farkle.gods.demeter import Demeter
from farkle.meta.save_manager import SaveManager
from farkle.ui.settings import WIDTH, HEIGHT


class GodSerializationTests(unittest.TestCase):
    """Test that god classes are properly serialized and deserialized."""
    
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()
    
    def setUp(self):
        """Set up a fresh game and save manager for each test."""
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1)
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.save_manager = SaveManager(save_path=self.temp_file.name)
        self.save_manager.attach(self.game)
    
    def tearDown(self):
        """Clean up temporary files."""
        import os
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
    
    def test_ares_serialization_preserves_type(self):
        """Test that Ares god type is preserved through save/load."""
        # Set up Ares as worshipped god
        ares = Ares(game=self.game)
        ares.level = 2
        self.game.gods.set_worshipped([ares])
        
        # Save and reload
        self.save_manager.save()
        save_data = self.save_manager.load()
        
        # Check saved data has correct type
        gods_data = save_data['gods']['worshipped']
        self.assertEqual(len(gods_data), 1)
        self.assertEqual(gods_data[0]['type'], 'Ares')
        self.assertEqual(gods_data[0]['name'], 'Ares')
        self.assertEqual(gods_data[0]['level'], 2)
        
        # Restore into new game
        new_game = Game(self.screen, self.font, self.clock, rng_seed=2)
        self.save_manager.game = new_game
        self.save_manager.restore_game_state(new_game, save_data)
        
        # Verify restored god is correct type
        self.assertEqual(len(new_game.gods.worshipped), 1)
        restored_god = new_game.gods.worshipped[0]
        self.assertIsInstance(restored_god, Ares)
        self.assertEqual(restored_god.name, 'Ares')
        self.assertEqual(restored_god.level, 2)
    
    def test_multiple_gods_serialization(self):
        """Test that multiple gods of different types are preserved."""
        # Set up multiple gods
        ares = Ares(game=self.game)
        ares.level = 1
        
        hermes = Hermes(game=self.game)
        hermes.level = 2
        
        demeter = Demeter(game=self.game)
        demeter.level = 3
        
        self.game.gods.set_worshipped([ares, hermes, demeter])
        
        # Save and reload
        self.save_manager.save()
        save_data = self.save_manager.load()
        
        # Restore into new game
        new_game = Game(self.screen, self.font, self.clock, rng_seed=3)
        self.save_manager.game = new_game
        self.save_manager.restore_game_state(new_game, save_data)
        
        # Verify all gods restored with correct types
        self.assertEqual(len(new_game.gods.worshipped), 3)
        
        restored_ares = new_game.gods.worshipped[0]
        self.assertIsInstance(restored_ares, Ares)
        self.assertEqual(restored_ares.level, 1)
        
        restored_hermes = new_game.gods.worshipped[1]
        self.assertIsInstance(restored_hermes, Hermes)
        self.assertEqual(restored_hermes.level, 2)
        
        restored_demeter = new_game.gods.worshipped[2]
        self.assertIsInstance(restored_demeter, Demeter)
        self.assertEqual(restored_demeter.level, 3)
    
    def test_all_four_gods_serialization(self):
        """Test serialization of all four current gods (limited to 3 worshipped at once)."""
        # Create all four gods with different levels
        gods = [
            Ares(game=self.game),
            Hermes(game=self.game),
            Hades(game=self.game),
            Demeter(game=self.game),
        ]
        
        # Set different levels
        for i, god in enumerate(gods, start=1):
            god.level = i
        
        # Note: set_worshipped only keeps first 3 gods (hard limit)
        self.game.gods.set_worshipped(gods)
        
        # Save and reload
        self.save_manager.save()
        save_data = self.save_manager.load()
        
        # Restore into new game
        new_game = Game(self.screen, self.font, self.clock, rng_seed=4)
        self.save_manager.game = new_game
        self.save_manager.restore_game_state(new_game, save_data)
        
        # Verify first 3 gods restored (max limit)
        self.assertEqual(len(new_game.gods.worshipped), 3)
        
        # Check types
        self.assertIsInstance(new_game.gods.worshipped[0], Ares)
        self.assertIsInstance(new_game.gods.worshipped[1], Hermes)
        self.assertIsInstance(new_game.gods.worshipped[2], Hades)
        
        # Check levels
        for i, god in enumerate(new_game.gods.worshipped, start=1):
            self.assertEqual(god.level, i)


if __name__ == '__main__':
    unittest.main()
