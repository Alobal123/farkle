import unittest
import pygame
from farkle.game import Game
from farkle.relics.relic import Relic
from farkle.scoring.scoring_manager import ScoreContext
from farkle.scoring.score_modifiers import ScoreModifier
from farkle.scoring.score_types import ScorePart

class PreScoreHook(ScoreModifier):
    def __init__(self, hook_function):
        self.hook_function = hook_function
        self.priority = 10 # Run early

    def apply(self, base: int, context: ScoreContext) -> int:
        score_obj = getattr(context, 'score_obj', None)
        if score_obj:
            new_parts = self.hook_function(context)
            if new_parts:
                score_obj.parts.extend(new_parts)
        return base

class HookRelic(Relic):
    def __init__(self):
        super().__init__(id="hooky", name='Hooky', cost=0, description="A test relic")
        self.add_modifier(PreScoreHook(self.hook_function))

    def hook_function(self, context: ScoreContext) -> list[ScorePart]:
        # Always add a 100-point bonus part
        return [ScorePart(rule_key="HookBonus", raw=100, adjusted=100)]

class RelicPreModHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1, 1), pygame.HIDDEN)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)
        # Inject our hook relic directly
        hr = HookRelic()
        self.game.relic_manager.active_relics.append(hr)
        hr.activate(self.game)

    def test_hook_adds_part(self):
        # Score a single 1 (100 raw)
        self.game.dice[0].value = 1
        for i in range(1, 6): self.game.dice[i].value = 2
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        
        # Preview should include the hook's bonus
        raw, selective, final, mult = self.game.selection_preview()
        self.assertEqual(raw, 100)
        self.assertEqual(selective, 200) # 100 from die + 100 from hook

if __name__ == '__main__':
    unittest.main()
