import unittest, pygame
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT

class ModifierAddRemovePreviewTests(unittest.TestCase):
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
        
        # Directly create and activate the "Charm of Fives" relic
        from farkle.relics.relic import Relic
        from farkle.scoring.score_modifiers import FlatRuleBonus
        
        charm_of_fives = Relic(
            id="charm_of_fives",
            name="Charm of Fives",
            cost=30,
            description="Get a flat bonus of 50 points for scoring with single 5s.",
            modifiers=[FlatRuleBonus(rule_key="SingleValue:5", amount=50)]
        )
        
        # Add the relic to the manager and activate it
        self.game.relic_manager.active_relics.append(charm_of_fives)
        charm_of_fives.activate(self.game)

    def _prep_single_five(self):
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i==0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True

    def test_preview_with_modifier_then_after_deactivate(self):
        self._prep_single_five()
        raw, selective, final, mult = self.game.selection_preview()
        self.assertEqual(raw, 50)
        self.assertEqual(selective, 100)
        # Deactivate relic (emit removal events)
        relic = self.game.relic_manager.active_relics[0]
        relic.deactivate(self.game)
        # Ensure removal events processed
        self._prep_single_five()
        raw2, selective2, final2, mult2 = self.game.selection_preview()
        self.assertEqual(raw2, 50)
        # After removal selective should equal raw again
        self.assertEqual(selective2, 50)

if __name__ == '__main__':
    unittest.main()
