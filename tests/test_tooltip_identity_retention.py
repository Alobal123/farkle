import unittest, pygame
from farkle.game import Game
from farkle.ui.screens.game_screen import GameScreen
from farkle.ui.settings import WIDTH, HEIGHT, TOOLTIP_DELAY_MS

class TooltipIdentityRetentionTests(unittest.TestCase):
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
        self.screen_wrapper = GameScreen(self.game)

    def test_identity_retention_over_extended_frames(self):
        self.game.draw()
        goal = self.game.level_state.goals[0]
        rect = getattr(goal, '_last_rect', None)
        self.assertIsNotNone(rect)
        if rect is None: return
        pos = (rect.x + 6, rect.y + 6)
        evt = pygame.event.Event(pygame.MOUSEMOTION, pos=pos)
        self.screen_wrapper.handle_event(evt)
        # Fast-forward beyond delay
        start_ms = pygame.time.get_ticks(); target_ms = start_ms + TOOLTIP_DELAY_MS + 60
        while pygame.time.get_ticks() < target_ms: pass
        self.screen_wrapper.draw(self.screen)
        first_id = self.screen_wrapper._current_tooltip.get('id') if self.screen_wrapper._current_tooltip else None
        self.assertIsNotNone(first_id, 'Tooltip should appear with identity')
        # Simulate several consecutive None resolutions by clearing rect repeatedly
        for i in range(15):
            saved = goal._last_rect
            goal._last_rect = None
            self.screen_wrapper.draw(self.screen)
            goal._last_rect = saved
            self.screen_wrapper.draw(self.screen)
            self.assertIsNotNone(self.screen_wrapper._current_tooltip, f'Tooltip should persist at cycle {i}')
            cur_id = self.screen_wrapper._current_tooltip.get('id')
            self.assertEqual(cur_id, first_id, 'Tooltip identity should remain stable')

if __name__ == '__main__':
    unittest.main()
