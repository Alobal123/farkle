import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class RelicDebugOverlayTests(unittest.TestCase):
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
        # Ensure gold and open shop
        self.game.player.gold = 500
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index":1}))
        # Buy first offer (Charm of Fives guaranteed at level 1)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC))
        # Force a draw call to build HUD & relic list (not strictly needed for debug lines method)
        self.game.renderer.draw()

    def test_debug_lines_include_relic(self):
        lines = self.game.renderer.get_active_relic_debug_lines()
        # Expect at least one line containing Charm of Fives
        self.assertTrue(any('Charm of Fives' in ln for ln in lines), f"Expected Charm of Fives in relic debug lines: {lines}")

if __name__ == '__main__':
    unittest.main()
