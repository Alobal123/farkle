import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType

class TestFarkleUI(unittest.TestCase):
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

    def test_farkle_banner_and_buttons(self):
        # Transition to FARKLE and ensure sprites reflect visibility rules.
        self.game.state_manager.transition_to_farkle()
        from farkle.core.game_state_enum import GameState
        self.assertEqual(self.game.state_manager.get_state(), GameState.FARKLE)
        # Trigger sprite update/draw cycle.
        self.game.renderer.draw()
        roll_btn = next((b for b in self.game.ui_buttons if b.name == 'roll'), None)
        bank_btn = next((b for b in self.game.ui_buttons if b.name == 'bank'), None)
        next_btn = next((b for b in self.game.ui_buttons if b.name == 'next'), None)
        self.assertIsNotNone(next_btn, 'Next button missing')
        # Hidden buttons (roll/bank) should have 1x1 image or be off-screen; next should be visible.
        if roll_btn and roll_btn.sprite:
            self.assertTrue(roll_btn.sprite.image.get_width() == 1 or roll_btn.sprite.rect.x < 0,
                            'Roll button sprite should be hidden during FARKLE')
        if bank_btn and bank_btn.sprite:
            self.assertTrue(bank_btn.sprite.image.get_width() == 1 or bank_btn.sprite.rect.x < 0,
                            'Bank button sprite should be hidden during FARKLE')
        if next_btn and next_btn.sprite:
            self.assertGreater(next_btn.sprite.image.get_width(), 1,
                               'Next button sprite should be visible during FARKLE')
        # Farkle banner removed; verify Next button label reflects Farkle state instead.
        next_btn = next((b for b in self.game.ui_buttons if b.name == 'next'), None)
        self.assertIsNotNone(next_btn, 'Next button should exist')
        if next_btn and hasattr(next_btn, 'label_fn') and callable(next_btn.label_fn):
            label = next_btn.label_fn(self.game)
        else:
            label = getattr(next_btn, 'label', '') if next_btn else ''
        self.assertTrue(
            isinstance(label, str) and (
                label.lower().startswith('next turn') or label.lower().startswith('skip rescue')
            ),
            f'Next button label should indicate next turn / skip rescue action, got: {label}'
        )

if __name__ == '__main__':
    unittest.main()
