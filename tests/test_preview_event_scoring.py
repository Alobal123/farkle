import unittest
import pygame
from farkle.game import Game
from farkle.relics.relic import Relic
from farkle.scoring.score_modifiers import RuleSpecificMultiplier
from farkle.core.game_event import GameEvent, GameEventType

class PreviewEventScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1, 1), pygame.HIDDEN)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)
        # Add rule specific doubling for SingleValue:5
        from farkle.relics.relic import Relic
        relic = Relic(id="preview_sigil", name="Preview Sigil", cost=0, description="A test relic.")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:5", mult=2.0))
        self.game.relic_manager.active_relics.append(relic)
        relic.on_activate(self.game)

    def test_selection_preview_uses_modifier_chain(self):
        # Force one die to be a 5
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i == 0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        # Preview score: raw 50, but with relic, selective should be 100
        raw, selective, final, mult = self.game.selection_preview()
        self.assertEqual(raw, 50)
        self.assertEqual(selective, 100)

if __name__ == '__main__':
    unittest.main()
