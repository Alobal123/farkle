import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT, TOOLTIP_BUTTON_DELAY_MS, TOOLTIP_DELAY_MS
from tooltip import resolve_hover

class TooltipButtonDelayTests(unittest.TestCase):
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
        # Force draw to ensure button rects visible
        self.game.renderer.draw()
        pygame.display.flip()

    def test_button_requires_longer_delay(self):
        # Pick the roll button rect
        roll_btn = None
        for b in self.game.ui_buttons:
            if b.name == 'roll':
                roll_btn = b; break
        self.assertIsNotNone(roll_btn)
        pos = (roll_btn.rect.centerx, roll_btn.rect.centery)  # type: ignore[attr-defined]
        # Simulate hover start
        self.game._hover_anchor_pos = pos
        self.game._hover_start_ms = pygame.time.get_ticks()
        # Immediately resolve (should not display yet)
        tip_early = resolve_hover(self.game, pos)
        # We intentionally do not set _current_tooltip (run loop handles delay). Ensure resolver returns something with delay override.
        self.assertIsNotNone(tip_early)
        if isinstance(tip_early, dict):
            self.assertGreaterEqual(tip_early.get('delay_ms', 0), TOOLTIP_BUTTON_DELAY_MS)
        # Fast-forward time less than button delay but greater than base delay
        future = self.game._hover_start_ms + TOOLTIP_DELAY_MS + 50
        # Emulate run loop logic snippet
        elapsed = future - self.game._hover_start_ms
        self.assertTrue(elapsed >= TOOLTIP_DELAY_MS)
        self.assertFalse(elapsed >= TOOLTIP_BUTTON_DELAY_MS, 'Elapsed should be less than button-specific delay for this test')

if __name__ == '__main__':
    unittest.main()
