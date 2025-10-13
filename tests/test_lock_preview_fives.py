import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class LockPreviewFivesTests(unittest.TestCase):
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
        # Fund and open shop
        self.game.player.gold = 500
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index":1}))
        # Purchase first offer (Charm of Fives guaranteed level 1)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC))
        # Ensure shop closed
        self.assertFalse(self.game.relic_manager.shop_open)

    def test_single_five_lock_shows_bonus_preview(self):
        # Force dice values: single five selectable
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i==0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        self.game.handle_lock()
        msg = self.game.message
        # Message should include raw->adjusted path '50 -> 100'
        self.assertIn('50 -> 100', msg, f"Expected preview '50 -> 100' in lock message, got: {msg}")

if __name__ == '__main__':
    unittest.main()
