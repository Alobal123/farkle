import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from score_modifiers import RuleSpecificMultiplier, FlatRuleBonus
from game_event import GameEventType

class ScoreModifierTests(unittest.TestCase):
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

    def _lock_single(self, value: int):
        d = self.game.dice[0]
        d.value = value; d.selected = True; d.scoring_eligible = True
        self.assertTrue(self.game._auto_lock_selection("Locked"))

    def test_rule_specific_multiplier_applies(self):
        # Double only SingleValue:1 using a rule-specific multiplier on a temporary relic
        from relic import Relic
        relic = Relic(name="Test Mult")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:1", mult=2.0))
        self.game.relic_manager.active_relics.append(relic)
        self.game.event_listener.subscribe(relic.on_event)
        self._lock_single(1)
        goal = self.game.level_state.goals[0]
        pre_remaining = goal.remaining
        self.game.handle_bank()
        self.assertEqual(pre_remaining - goal.remaining, 200)

    def test_event_sequence_unchanged(self):
        captured = []
        def cap(ev):
            if ev.type in (GameEventType.SCORE_APPLY_REQUEST, GameEventType.SCORE_APPLIED, GameEventType.GOAL_PROGRESS):
                captured.append(ev.type)
        self.game.event_listener.subscribe(cap)
        self._lock_single(1)
        self.game.handle_bank()
        self.assertGreaterEqual(len(captured), 3)
        self.assertEqual(captured[0], GameEventType.SCORE_APPLY_REQUEST)
        self.assertEqual(captured[1], GameEventType.SCORE_APPLIED)
        self.assertEqual(captured[2], GameEventType.GOAL_PROGRESS)

if __name__ == '__main__':
    unittest.main()
