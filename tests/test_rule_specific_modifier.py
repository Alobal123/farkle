import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType
from score_modifiers import RuleSpecificMultiplier, ScoreMultiplier

class RuleSpecificModifierTests(unittest.TestCase):
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
        # Inject a relic with a rule-specific multiplier doubling only SingleValue 5's
        from relic import Relic
        relic = Relic(name="Test Sigil")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:5", mult=2.0))
        self.game.relic_manager.active_relics.append(relic)
        self.game.event_listener.subscribe(relic.on_event)

    def test_double_only_single_fives(self):
        # Force dice: two scoring singles 5 (should be 2 * 50 = 100 raw) and one single 1 (100) -> separate locks
        # We'll test applying a single lock of two 5s.
        # Set dice manually: first roll situation
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i < 2 else 2  # first two are 5 scoring singles
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        # Select first two dice (5s)
        for i,d in enumerate(self.game.dice[:2]):
            d.selected = True
        # Ensure selection recognized as a single combo (two singles count as two combos, so lock individually)
        # Lock first die (5) twice sequentially to build pending then bank.
        # We'll mimic two separate single-value locks:
        for single_index in range(2):
            # Deselect all then select one 5
            for d in self.game.dice:
                d.selected = False
            self.game.dice[single_index].selected = True
            # Perform lock via action pipeline
            self.game.handle_lock()
        # At this point pending_raw on the goal should be 100 (two singles of 50)
        goal = self.game.level_state.goals[0]
        self.assertEqual(goal.pending_raw, 100)
        # Bank and capture SCORE_APPLIED payload
        captured = {}
        def cap(ev):
            if ev.type == GameEventType.SCORE_APPLIED:
                captured.update(ev.payload)
        self.game.event_listener.subscribe(cap)
        self.game.handle_bank()
        # Simulate progression of SCORE_APPLY_REQUEST cycle
        # (Events triggered synchronously inside handle_bank())
        # Pending raw now reflects mutated total after selective doubling (100 -> 200)
        self.assertEqual(captured.get("pending_raw"), 200)
        self.assertEqual(captured.get("adjusted"), 200)
        # Ensure score structure present and reflects selective doubling
        self.assertIn("score", captured)
        score_obj = captured["score"]
        self.assertIn("parts", score_obj)
        parts = score_obj["parts"]
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["rule_key"], "SingleValue:5")
        # Raw still reports pre-mutation aggregated raw; adjusted reflects doubled value
        self.assertEqual(parts[0]["raw"], 100)
        self.assertEqual(parts[0]["adjusted"], 200)

if __name__ == '__main__':
    unittest.main()
