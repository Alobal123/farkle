import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType

class ScoringEventOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)
        self.game.state_manager.transition_to_rolling()
        # Capture events in order
        self.captured = []
        def cap(ev):
            if ev.type in (GameEventType.SCORE_APPLY_REQUEST, GameEventType.SCORE_APPLIED,
                           GameEventType.GOAL_PROGRESS, GameEventType.GOAL_FULFILLED,
                           GameEventType.BANK, GameEventType.TURN_BANKED, GameEventType.TURN_END):
                self.captured.append(ev.type)
        self.game.event_listener.subscribe(cap)

    def prepare_scoring_die(self, idx: int, value: int):
        d = self.game.dice[idx]
        d.value = value
        d.selected = True
        d.scoring_eligible = True

    def test_scoring_application_event_sequence(self):
        # Lock two singles (1s) in separate locks, then bank -> expect request/apply before goal progress
        goal = self.game.level_state.goals[0]
        self.prepare_scoring_die(0, 1)
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        # Second single
        d = self.game.dice[1]; d.value = 1; d.selected = True; d.scoring_eligible = True
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        pre_remaining = goal.remaining
        self.game.handle_bank()
        # Basic sanity: goal remaining decreased
        self.assertLess(goal.remaining, pre_remaining)
        # Extract ordering subsequence
        try:
            req_index = self.captured.index(GameEventType.SCORE_APPLY_REQUEST)
            applied_index = self.captured.index(GameEventType.SCORE_APPLIED)
            progress_index = self.captured.index(GameEventType.GOAL_PROGRESS)
        except ValueError:
            self.fail(f"Missing expected events in captured sequence: {self.captured}")
        self.assertLess(req_index, applied_index, "Request should precede applied")
        self.assertLess(applied_index, progress_index, "Applied should precede progress")

if __name__ == '__main__':
    unittest.main()
