import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class TestSecondLevelDiceHiddenUntilRoll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)
        # Use helper to advance level and close shop
        self.game.testing_advance_level()
        # Now we should be at level_index 2 and in PRE_ROLL with dice hidden
        self.assertEqual(self.game.level_index, 2)
        self.assertEqual(self.game.state_manager.get_state(), self.game.state_manager.state.PRE_ROLL)
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Dice should not draw at second level start before first roll')

    def test_second_level_dice_unhide_on_roll(self):
        self.game.handle_roll()
        for d in self.game.dice:
            self.assertTrue(d.should_draw(self.game), 'Dice should draw after first second-level roll')

if __name__ == '__main__':
    unittest.main()
