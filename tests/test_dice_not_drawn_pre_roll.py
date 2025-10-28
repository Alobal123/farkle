import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

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
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)

    def test_initial_level_dice_not_drawn_before_roll(self):
        # PRE_ROLL: retain logical visibility check; sprite may not yet have run update cycle.
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Die should not draw before first roll')
        self.game.handle_roll()
        for d in self.game.dice:
            self.assertTrue(d.should_draw(self.game), 'Die should draw after first roll')

    def test_post_shop_dice_not_drawn_before_roll(self):
        # Advance level via proper event flow: trigger advancement and close shop
        # Call create_next_level directly to advance
        self.game.create_next_level()
        # Ensure shop opened
        self.assertTrue(self.game.relic_manager.shop_open, 'Shop should be open after level advance')
        # Close shop via event to complete advancement
        self.game.event_listener.publish(GameEvent(GameEventType.SHOP_CLOSED, payload={"skipped": True}))
        # Now we should be in PRE_ROLL at level 2
        self.assertEqual(self.game.state_manager.get_state(), self.game.state_manager.state.PRE_ROLL)
        self.assertEqual(self.game.level_index, 2)
        # Dice should not draw before roll
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Die should not draw before roll after shop')
        self.game.handle_roll()
        for d in self.game.dice:
            self.assertTrue(d.should_draw(self.game), 'Die should draw after first roll following shop close')

if __name__ == '__main__':
    unittest.main()
