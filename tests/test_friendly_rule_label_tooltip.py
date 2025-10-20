import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.ui.tooltip import resolve_hover, friendly_rule_label

class FriendlyRuleLabelTooltipTests(unittest.TestCase):
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
        self.game.state_manager.transition_to_rolling()
        # Create a three-of-a-kind selection (e.g., 2,2,2)
        for i, d in enumerate(self.game.dice):
            d.value = 2 if i < 3 else 5
            d.scoring_eligible = True if i < 3 else False
            d.selected = True if i < 3 else False
        # Auto-lock selection
        self.game._auto_lock_selection("Locked")
        self.game.renderer.draw()
        pygame.display.flip()

    def test_locked_three_kind_label(self):
        # Hover over one of the locked dice
        d0 = self.game.dice[0]
        pos = (d0.rect().centerx, d0.rect().centery)
        tip = resolve_hover(self.game, pos)
        self.assertIsNotNone(tip)
        lines = tip.get('lines', []) if isinstance(tip, dict) else []
        # Expect human-friendly 'Three 2s'
        self.assertTrue(any('Three 2s' in ln for ln in lines), f"Tooltip lines missing friendly label: {lines}")

    def test_helper_direct(self):
        self.assertEqual(friendly_rule_label('ThreeOfAKind:6'), 'Three 6s')
        self.assertEqual(friendly_rule_label('SingleValue:1'), 'Single 1')
        self.assertEqual(friendly_rule_label('Straight6'), 'Straight 1-6')

if __name__ == '__main__':
    unittest.main()
