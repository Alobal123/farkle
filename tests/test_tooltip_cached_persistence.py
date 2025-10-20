import unittest, pygame
from farkle.game import Game
from farkle.ui.screens.game_screen import GameScreen
from farkle.ui.settings import WIDTH, HEIGHT, TOOLTIP_DELAY_MS

class TooltipCachedPersistenceTests(unittest.TestCase):
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

    def test_tooltip_persists_over_many_frames(self):
        # Prime goal rect
        self.game.draw()
        goal = self.game.level_state.goals[0]
        rect = getattr(goal, '_last_rect', None)
        self.assertIsNotNone(rect)
        if rect is None: return
        pos = (rect.x + 5, rect.y + 5)
        evt = pygame.event.Event(pygame.MOUSEMOTION, pos=pos)
        self.screen_wrapper.handle_event(evt)
        # Fast-forward time beyond delay
        start_ms = pygame.time.get_ticks(); target_ms = start_ms + TOOLTIP_DELAY_MS + 60
        while pygame.time.get_ticks() < target_ms: pass
        # Draw to show tooltip
        self.screen_wrapper.draw(self.screen)
        self.assertIsNotNone(self.screen_wrapper._current_tooltip, 'Tooltip should appear')
        # Run many frames; mutate goal rect intermittently
        for i in range(25):
            if i % 7 == 0:
                # Temporarily remove last_rect
                saved = goal._last_rect
                goal._last_rect = None
                self.screen_wrapper.draw(self.screen)
                goal._last_rect = saved
            else:
                self.screen_wrapper.draw(self.screen)
            self.assertIsNotNone(self.screen_wrapper._current_tooltip, f'Tooltip should persist at frame {i}')

if __name__ == '__main__':
    unittest.main()
