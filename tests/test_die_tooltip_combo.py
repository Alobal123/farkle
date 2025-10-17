import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from tooltip import resolve_hover
from game_event import GameEvent, GameEventType

class DieTooltipComboTests(unittest.TestCase):
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
        # Force into rolling state
        self.game.state_manager.transition_to_rolling()
        # Make a single scoring 1
        d0 = self.game.dice[0]
        d0.value = 1
        d0.scoring_eligible = True
        d0.selected = True
        # Lock it via game auto-lock logic
        self.game._auto_lock_selection("Locked")
        # Ensure renderer ran to set rects
        self.game.renderer.draw()
        pygame.display.flip()

    def test_held_die_shows_locked_combo(self):
        d0 = self.game.dice[0]
        self.assertTrue(d0.held)
        pos = (d0.rect().centerx, d0.rect().centery)
        tip = resolve_hover(self.game, pos)
        self.assertIsNotNone(tip)
        lines = tip.get('lines', []) if isinstance(tip, dict) else []
        self.assertTrue(any('Locked:' in ln for ln in lines), f"Expected locked combo info in tooltip lines: {lines}")

if __name__ == '__main__':
    unittest.main()
