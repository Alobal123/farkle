"""Test temple income awarded at level start."""
import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class TempleIncomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'):
            flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)

    def test_initial_income_is_30(self):
        """Player starts with 30 temple income."""
        self.assertEqual(self.game.player.temple_income, 30)

    def test_temple_income_awards_gold_on_level_start(self):
        """When temple_income > 0, gold is awarded at level start."""
        # Set temple income
        self.game.player.temple_income = 10
        initial_gold = self.game.player.gold
        
        # Emit LEVEL_GENERATED event
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_GENERATED, payload={}))
        
        # Gold should increase by temple income
        self.assertEqual(self.game.player.gold, initial_gold + 10)

    def test_temple_income_zero_awards_nothing(self):
        """When temple_income is 0, no gold is awarded."""
        self.game.player.temple_income = 0
        initial_gold = self.game.player.gold
        
        # Emit LEVEL_GENERATED event
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_GENERATED, payload={}))
        
        # Gold should not change
        self.assertEqual(self.game.player.gold, initial_gold)

    def test_temple_income_multiple_levels(self):
        """Temple income is awarded each level."""
        self.game.player.temple_income = 5
        initial_gold = self.game.player.gold
        
        # Emit 3 level generations
        for _ in range(3):
            self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_GENERATED, payload={}))
        
        # Gold should increase by 5 * 3 = 15
        self.assertEqual(self.game.player.gold, initial_gold + 15)

if __name__ == '__main__':
    unittest.main()
