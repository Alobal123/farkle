import unittest, pygame
from game import Game
from screens.game_screen import GameScreen
from settings import WIDTH, HEIGHT, TOOLTIP_DELAY_MS

class TooltipJitterThresholdTests(unittest.TestCase):
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

    def test_small_mouse_jitter_does_not_hide_tooltip(self):
        # Prime goal rects
        self.game.draw()
        first_goal = self.game.level_state.goals[0]
        rect = getattr(first_goal, '_last_rect', None)
        self.assertIsNotNone(rect, 'Goal rect should be initialized after draw')
        if rect is None: return
        base_pos = (rect.x + 4, rect.y + 4)
        # Anchor hover
        evt = pygame.event.Event(pygame.MOUSEMOTION, pos=base_pos)
        self.screen_wrapper.handle_event(evt)
        # Fast-forward time beyond delay
        start_ms = pygame.time.get_ticks(); target_ms = start_ms + TOOLTIP_DELAY_MS + 40
        while pygame.time.get_ticks() < target_ms: pass
        self.screen_wrapper.draw(self.screen)
        self.assertIsNotNone(self.screen_wrapper._current_tooltip, 'Tooltip should be visible after delay')
        # Apply small jitter movements within threshold (<3px)
        jitter_positions = [ (base_pos[0]+1, base_pos[1]), (base_pos[0], base_pos[1]+2), (base_pos[0]-1, base_pos[1]-1) ]
        for jp in jitter_positions:
            evt2 = pygame.event.Event(pygame.MOUSEMOTION, pos=jp)
            self.screen_wrapper.handle_event(evt2)
            # Draw to allow internal logic to possibly clear
            self.screen_wrapper.draw(self.screen)
            self.assertIsNotNone(self.screen_wrapper._current_tooltip, f'Tooltip should persist through jitter at {jp}')

if __name__ == '__main__':
    unittest.main()
