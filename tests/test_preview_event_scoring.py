import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType
from farkle.scoring.score_modifiers import RuleSpecificMultiplier

class PreviewEventScoringTests(unittest.TestCase):
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
        # Add rule specific doubling for SingleValue:5
        from farkle.relics.relic import Relic
        relic = Relic(name="Preview Sigil")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:5", mult=2.0))
        self.game.relic_manager.active_relics.append(relic)
        self.game.event_listener.subscribe(relic.on_event)
        self.captured_preview = None
        def cap(ev):
            if ev.type == GameEventType.SCORE_PREVIEW_COMPUTED:
                self.captured_preview = ev.payload
        self.game.event_listener.subscribe(cap)

    def _force_single_five(self):
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i==0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice(); self.game.dice[0].selected = True

    def test_selection_preview_uses_modifier_chain(self):
        self._force_single_five()
        raw, adjusted, final_, mult = self.game.selection_preview()
        self.assertEqual(raw, 50)
        self.assertEqual(adjusted, 100, "Adjusted should reflect doubling modifier")
        self.assertEqual(final_, adjusted)
        # Lean mode: no preview events; ensure captured_preview remains None
        self.assertIsNone(self.captured_preview, "Preview events removed in lean scoring manager")

if __name__ == '__main__':
    unittest.main()
