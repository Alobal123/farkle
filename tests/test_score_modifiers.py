import unittest
import pygame
from farkle.game import Game
from farkle.relics.relic import Relic
from farkle.scoring.score_modifiers import RuleSpecificMultiplier
from farkle.core.game_event import GameEventType

class ScoreModifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1, 1), pygame.HIDDEN)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)

    def _lock_single(self, val):
        self.game.dice[0].value = val
        for i in range(1, 6): self.game.dice[i].value = val + 1
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        self.game.handle_lock()

    def test_rule_specific_multiplier_applies(self):
        # Double only SingleValue:1 using a rule-specific multiplier on a temporary relic
        relic = Relic(id="test_mult", name="Test Mult", cost=0, description="A test relic.")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:1", mult=2.0))
        self.game.relic_manager.active_relics.append(relic)
        relic.on_activate(self.game)
        
        self._lock_single(1) # 100 raw
        
        captured = {}
        def cap(ev):
            if ev.type == GameEventType.SCORE_APPLIED:
                captured.update(ev.payload)
        self.game.event_listener.subscribe(cap)
        
        self.game.handle_bank()
        
        self.assertEqual(captured.get("pending_raw"), 200)
        self.assertEqual(captured.get("adjusted"), 200)

    def test_event_sequence_unchanged(self):
        captured = []
        def cap(ev):
            if ev.type in (GameEventType.SCORE_APPLY_REQUEST, GameEventType.SCORE_APPLIED, GameEventType.GOAL_PROGRESS):
                captured.append(ev.type)
        self.game.event_listener.subscribe(cap)
        self._lock_single(1)
        self.game.handle_bank()
        expected = [GameEventType.SCORE_APPLY_REQUEST, GameEventType.SCORE_APPLIED, GameEventType.GOAL_PROGRESS]
        self.assertEqual(captured, expected)

if __name__ == '__main__':
    unittest.main()
