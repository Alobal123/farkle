import unittest
import pygame
from farkle.game import Game
from farkle.relics.relic import Relic
from farkle.scoring.score_modifiers import RuleSpecificMultiplier

class RuleSpecificModifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1, 1), pygame.HIDDEN)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)
        # Inject a relic with a rule-specific multiplier doubling only SingleValue 5's
        from farkle.relics.relic import Relic
        relic = Relic(id="test_sigil", name="Test Sigil", cost=0, description="A test relic.")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:5", mult=2.0))
        self.game.relic_manager.active_relics.append(relic)
        relic.on_activate(self.game)

    def test_double_only_single_fives(self):
        # Score a single 5 (50 raw)
        self.game.dice[0].value = 5
        for i in range(1, 6): self.game.dice[i].value = 2
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        
        raw, selective, final, mult = self.game.selection_preview()
        self.assertEqual(raw, 50)
        self.assertEqual(selective, 100)

        # Score a single 1 (100 raw) - should not be doubled
        self.game.dice[0].value = 1
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        raw, selective, final, mult = self.game.selection_preview()
        self.assertEqual(raw, 100)
        self.assertEqual(selective, 100)

if __name__ == '__main__':
    unittest.main()
