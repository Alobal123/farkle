import unittest, pygame, random
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class TestFarkleRescuePreservesPending(unittest.TestCase):
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
        # Roll once so we can lock something
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')
        # Force dice to contain a scoring single (1) for first die
        d0 = self.game.dice[0]; d0.value = 1; d0.selected = True; d0.scoring_eligible = True
        self.game.update_current_selection_score()
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        goal = self.game.level_state.goals[0]
        self.assertGreater(goal.pending_raw, 0)
        locked_pending = goal.pending_raw
        # Now create a farkle pattern with remaining dice (all non-scoring)
        pattern = [2,3,4,6,2,3]
        # Skip first die (already held); assign to others
        idx = 0
        for die in self.game.dice:
            if die.held: continue
            die.value = pattern[idx % len(pattern)]
            die.selected = False
            die.scoring_eligible = False
            idx += 1
        self.game.mark_scoring_dice(); self.assertTrue(self.game.check_farkle())
        # Transition to FARKLE -> should NOT clear pending because reroll available
        self.game.state_manager.transition_to_farkle()
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        self.assertEqual(goal.pending_raw, locked_pending, 'Pending should be preserved during rescuable FARKLE')
        # Activate reroll selection and force a rescue (rerolled die becomes 1)
        reroll = self.game.ability_manager.get('reroll'); self.assertIsNotNone(reroll)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
        reroll = self.game.ability_manager.get('reroll'); self.assertTrue(reroll and reroll.selecting)
        original_randint = random.randint; random.randint = lambda a,b: 1
        try:
            target_index = next(i for i,d in enumerate(self.game.dice) if not d.held)
            self.assertTrue(self.game.ability_manager.attempt_target('die', target_index))
        finally:
            random.randint = original_randint
        # After rescue state back to ROLLING; pending still intact
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')
        self.assertEqual(goal.pending_raw, locked_pending, 'Pending should persist after successful rescue')
        # Now intentionally create an unrecoverable farkle (exhaust reroll) and ensure pending only clears on TURN_END
        reroll = self.game.ability_manager.get('reroll')
        if reroll:
            reroll.charges_used = reroll.charges_per_level
        pattern2 = [2,3,4,6,2,3]
        for die in self.game.dice:
            if die.held: continue
            die.value = pattern2[0]; die.selected = False; die.scoring_eligible = False
        self.game.mark_scoring_dice(); self.assertTrue(self.game.check_farkle())
        self.game.event_listener.publish(GameEvent(GameEventType.FARKLE, payload={}))
        self.assertEqual(goal.pending_raw, locked_pending, 'Pending should still persist after unrecoverable FARKLE before TURN_END')
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason":"farkle"}))
        self.assertEqual(goal.pending_raw, 0, 'Pending should clear only on farkle TURN_END finalization')

if __name__ == '__main__':
    unittest.main()
