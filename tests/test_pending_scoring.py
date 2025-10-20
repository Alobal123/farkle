import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class PendingScoringTests(unittest.TestCase):
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

    def prepare_scoring_die(self, die_index: int, value: int):
        d = self.game.dice[die_index]
        d.value = value
        d.selected = True
        d.scoring_eligible = True

    def test_multiple_locks_accumulate_same_goal(self):
        goal = self.game.level_state.goals[0]
        # First lock: single 1 (100)
        self.prepare_scoring_die(0, 1)
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        self.assertEqual(goal.pending_raw, 100)
        # Second lock: another single 1
        d = self.game.dice[1]
        d.value = 1; d.selected = True; d.scoring_eligible = True
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        self.assertEqual(goal.pending_raw, 200)
        # Bank applies 200 (no global multipliers)
        pre_remaining = goal.remaining
        self.game.handle_bank()
        self.assertEqual(pre_remaining - goal.remaining, 200)

    def test_locks_across_two_goals(self):
        # Ensure at least two goals; if only one, add a temporary second by adjusting level state.
        if len(self.game.level_state.goals) == 1:
            # Extend manually (test-only) by appending a new Goal clone
            from farkle.goals.goal import Goal
            new_goal = Goal(150, name="Temp", mandatory=False, reward_gold=0)
            self.game.level_state.goals.append(new_goal)
            # Also wire into event system
            new_goal.game = self.game  # type: ignore[attr-defined]
            self.game.event_listener.subscribe(new_goal.on_event)
            # Also extend the immutable level definition tuple so name lookups succeed
            self.game.level = type(self.game.level)(
                name=self.game.level.name,
                max_turns=self.game.level.max_turns,
                description=self.game.level.description,
                # score_multiplier removed from Level; no field to pass now
                goals=self.game.level.goals + (("Temp", 150, False, 0),)
            )
        g0, g1 = self.game.level_state.goals[0], self.game.level_state.goals[1]
        # Lock to goal 0
        self.prepare_scoring_die(0, 1)
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        self.assertEqual(g0.pending_raw, 100)
        # Switch active goal and lock another scoring die
        self.game.active_goal_index = 1
        # Choose a fresh unheld die (next unheld index after first lock). First lock holds die[0].
        d = next(die for die in self.game.dice if not die.held)
        # Clear selection flags before new pick
        for dclr in self.game.dice:
            if not dclr.held:
                dclr.selected = False
                dclr.scoring_eligible = False
        d.value = 1
        d.selected = True
        d.scoring_eligible = True
        # Update current selection score to reflect new selection
        self.game.update_current_selection_score()
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        self.assertEqual(g1.pending_raw, 100)
        # Bank: both apply
        pre0, pre1 = g0.remaining, g1.remaining
        self.game.handle_bank()
        self.assertEqual(pre0 - g0.remaining, 100)
        self.assertEqual(pre1 - g1.remaining, 100)

    def test_farkle_clears_pending(self):
        goal = self.game.level_state.goals[0]
        # Set up one lock
        self.prepare_scoring_die(0, 1)
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        self.assertGreater(goal.pending_raw, 0)
        # Simulate a farkle: publish FARKLE event directly
        self.game.event_listener.publish(GameEvent(GameEventType.FARKLE, payload={}))
        self.assertEqual(goal.pending_raw, 0, "Pending should clear on FARKLE")

if __name__ == '__main__':
    unittest.main()
