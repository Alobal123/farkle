import pygame, unittest
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType
from relic import Relic
from score_types import ScorePart

class HookRelic(Relic):
    def on_event(self, event):  # type: ignore[override]
        if event.type == GameEventType.SCORE_PRE_MODIFIERS:
            score_obj = event.get('score_obj')
            if score_obj:
                # Add a synthetic +25 bonus part
                score_obj.add_part(ScorePart(rule_key='SyntheticBonus', raw=25))

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
        hr = HookRelic(name='Hooky')
        self.game.relic_manager.active_relics.append(hr)
        self.game.event_listener.subscribe(hr.on_event)

    def test_hook_adds_part(self):
        # Simulate a score application with pending_raw 50 for SingleValue:5
        parts = [{'rule_key': 'SingleValue:5', 'raw': 50, 'adjusted': None}]
        payload = {'goal': self.game.level_state.goals[0], 'pending_raw': 50, 'score': {'detailed_parts': parts, 'parts': parts}}
        captured = []
        pre_seen = {"count":0}
        def cap(ev):
            if ev.type == GameEventType.SCORE_APPLIED:
                captured.append(ev)
            if ev.type == GameEventType.SCORE_PRE_MODIFIERS:
                pre_seen["count"] += 1
        self.game.event_listener.subscribe(cap)
        # Single publish; hook relic already subscribed in setUp and should mutate before modifiers
        self.game.event_listener.publish(GameEvent(GameEventType.SCORE_APPLY_REQUEST, payload=payload))
        self.assertTrue(captured, 'Expected SCORE_APPLIED event')
        self.assertGreaterEqual(pre_seen["count"], 1, 'Expected SCORE_PRE_MODIFIERS event')
        applied = captured[-1].payload
        self.assertGreaterEqual(applied.get('adjusted', 0), 75)
        score = applied.get('score', {})
        detailed = score.get('detailed_parts', [])
        has_bonus = any(p.get('rule_key') == 'SyntheticBonus' for p in detailed)
        self.assertTrue(has_bonus, 'Synthetic bonus part not found in detailed parts')

if __name__ == '__main__':
    unittest.main()
