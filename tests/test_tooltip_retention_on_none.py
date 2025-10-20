import unittest, pygame
from farkle.game import Game
from farkle.ui.screens.game_screen import GameScreen
from farkle.ui.settings import WIDTH, HEIGHT, TOOLTIP_DELAY_MS

class TooltipRetentionOnNoneTests(unittest.TestCase):
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

    def test_tooltip_retains_when_resolver_none(self):
        # Prime goal rect
        self.game.draw()
        first_goal = self.game.level_state.goals[0]
        rect = getattr(first_goal, '_last_rect', None)
        self.assertIsNotNone(rect)
        if rect is None: return
        base_pos = (rect.x + 4, rect.y + 4)
        evt = pygame.event.Event(pygame.MOUSEMOTION, pos=base_pos)
        self.screen_wrapper.handle_event(evt)
        # Fast-forward time beyond delay
        start_ms = pygame.time.get_ticks(); target_ms = start_ms + TOOLTIP_DELAY_MS + 40
        while pygame.time.get_ticks() < target_ms: pass
        # Show tooltip
        self.screen_wrapper.draw(self.screen)
        self.assertIsNotNone(self.screen_wrapper._current_tooltip, 'Tooltip should be visible after delay')
        # Simulate intermittent None by temporarily clearing goal _last_rect
        saved_rect = first_goal._last_rect
        first_goal._last_rect = None
        # Draw frame: resolver returns None but mouse still over original rect area
        self.screen_wrapper.draw(self.screen)
        # Restore rect
        first_goal._last_rect = saved_rect
        # Tooltip should still be retained
        self.assertIsNotNone(self.screen_wrapper._current_tooltip, 'Tooltip should persist through transient None resolver')

if __name__ == '__main__':
    unittest.main()
