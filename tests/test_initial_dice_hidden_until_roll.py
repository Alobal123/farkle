import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT

class TestInitialDiceHiddenUntilRoll(unittest.TestCase):
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
        # Initial turn should have dice hidden now
        # Sprite gating: run update then verify hidden (image 1x1 or off-screen)
        self.game.renderer.draw()
        for d in self.game.dice:
            self.assertTrue(hasattr(d, 'sprite') and d.sprite is not None, 'Die should have sprite attached')
            s = d.sprite
            self.assertTrue(s.image.get_width() == 1 or s.rect.x < 0,
                            'Die sprite should be hidden in PRE_ROLL')

    def test_dice_become_visible_after_first_roll(self):
        self.game.handle_roll()
        self.game.renderer.draw()
        for d in self.game.dice:
            s = d.sprite
            self.assertGreater(s.image.get_width(), 1, 'Die sprite should be visible after first roll')
            self.assertGreaterEqual(s.rect.x, 0, 'Die sprite should be on-screen after first roll')

if __name__ == '__main__':
    unittest.main()
