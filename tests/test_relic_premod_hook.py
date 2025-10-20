import pygame, unittest
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType
from farkle.relics.relic import Relic
from farkle.scoring.score_types import ScorePart

from farkle.scoring.score_modifiers import FlatRuleBonus

class HookRelic(Relic):
    """Relic used to validate centralized modifier chain without legacy pre-mod hook.

    Adds a FlatRuleBonus (+25) to SingleValue:5 via SCORE_MODIFIER_ADDED on activation.
    """
    def __init__(self):
        super().__init__(name='Hooky')
        self.add_modifier(FlatRuleBonus(rule_key='SingleValue:5', amount=25))

class RelicPreModHookTests(unittest.TestCase):
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
        # Inject our hook relic directly
        hr = HookRelic()
        # Force activation sequence to emit SCORE_MODIFIER_ADDED
        hr.active = False
        hr.activate(self.game)
        self.game.relic_manager.active_relics.append(hr)

    def test_hook_adds_part(self):
        # Simulate a score application with pending_raw 50 for SingleValue:5
        parts = [{'rule_key': 'SingleValue:5', 'raw': 50, 'adjusted': None}]
        payload = {'goal': self.game.level_state.goals[0], 'pending_raw': 50, 'score': {'detailed_parts': parts, 'parts': parts}}
        captured = []
        def cap(ev):
            if ev.type == GameEventType.SCORE_APPLIED:
                captured.append(ev)
        self.game.event_listener.subscribe(cap)
        # Publish apply request (chain will adjust part via ScoringManager)
        self.game.event_listener.publish(GameEvent(GameEventType.SCORE_APPLY_REQUEST, payload=payload))
        self.assertTrue(captured, 'Expected SCORE_APPLIED event')
        applied = captured[-1].payload
        # Adjusted should reflect raw 50 + flat bonus 25 = 75
        self.assertEqual(applied.get('pending_raw'), 75)
        self.assertEqual(applied.get('adjusted'), 75)
        score = applied.get('score', {})
        detailed = score.get('parts', []) or score.get('detailed_parts', [])
        # SingleValue:5 part should show adjusted 75
        sv5 = next((p for p in detailed if p.get('rule_key') == 'SingleValue:5'), None)
        self.assertIsNotNone(sv5)
        if sv5 is not None:
            self.assertIn('adjusted', sv5)
            self.assertEqual(sv5.get('adjusted'), 75)

if __name__ == '__main__':
    unittest.main()
