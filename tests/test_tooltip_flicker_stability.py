import unittest, pygame
from game import Game
from screens.game_screen import GameScreen
from settings import WIDTH, HEIGHT, TOOLTIP_DELAY_MS

class TooltipFlickerStabilityTests(unittest.TestCase):
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

    def test_goal_tooltip_stable_over_frames(self):
        # Hover over first goal rect (simulate after initial draw to populate _last_rect)
        self.game.draw()
        first_goal = self.game.level_state.goals[0]
        rect = getattr(first_goal, '_last_rect', None)
        self.assertIsNotNone(rect, 'Goal rect should be initialized after draw')
        if rect is None: return
        # Simulate mouse motion event to anchor hover
        evt = pygame.event.Event(pygame.MOUSEMOTION, pos=(rect.x+2, rect.y+2))
        self.screen_wrapper.handle_event(evt)
        # Fast-forward time to exceed delay
        start_ms = pygame.time.get_ticks()
        target_ms = start_ms + TOOLTIP_DELAY_MS + 50
        while pygame.time.get_ticks() < target_ms:
            pass  # busy wait; small scope
        # Perform multiple draw cycles and assert tooltip persists
        visible_counts = 0
        for _ in range(8):
            self.screen_wrapper.draw(self.screen)
            if self.screen_wrapper._current_tooltip:
                visible_counts += 1
        self.assertGreaterEqual(visible_counts, 7, f"Tooltip should remain visible on most frames, got {visible_counts}/8")

if __name__ == '__main__':
    unittest.main()
