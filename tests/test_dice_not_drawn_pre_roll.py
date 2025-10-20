import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT

class TestDiceNotDrawnPreRoll(unittest.TestCase):
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

    def test_initial_level_dice_not_drawn_before_roll(self):
        # PRE_ROLL: retain logical visibility check; sprite may not yet have run update cycle.
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Die should not draw before first roll')
        self.game.handle_roll()
        for d in self.game.dice:
            self.assertTrue(d.should_draw(self.game), 'Die should draw after first roll')

    def test_post_shop_dice_not_drawn_before_roll(self):
        # Advance level via helper then confirm dice hidden and not drawn
        self.game.testing_advance_level()
        self.assertEqual(self.game.state_manager.get_state(), self.game.state_manager.state.PRE_ROLL)
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Die should not draw before roll after shop')
        self.game.handle_roll()
        for d in self.game.dice:
            self.assertTrue(d.should_draw(self.game), 'Die should draw after first roll following shop close')

if __name__ == '__main__':
    unittest.main()
