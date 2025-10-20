import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class GoalPendingPreviewTests(unittest.TestCase):
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
        self.game.player.gold = 500
        # Open shop and buy Charm of Fives
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={'level_index':1}))
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC))

    def test_single_five_pending_preview(self):
        # Lock a single five
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i==0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice(); self.game.dice[0].selected = True
        self.game.handle_lock()
        # Directly use game's authoritative computation (renderer shim removed)
        projected = self.game.level_state.goals[0].projected_pending()
        self.assertEqual(projected, 100)

if __name__ == '__main__':
    unittest.main()
