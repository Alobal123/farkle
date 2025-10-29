"""Unittest version of banking reward and hot dice tests.

Pytest could not be installed in the current runtime environment; these tests
provide equivalent coverage using the built-in unittest framework.
"""
import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.actions import handle_bank, handle_roll

class BankingAndHotDiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'):
            flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        # Initialize game but skip god selection for this test
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)

    def make_goal_easy(self):
        # Use a petition goal (not disaster) since disasters have no rewards
        petition_goals = [g for g in self.game.level_state.goals if not g.is_disaster]
        if petition_goals:
            petition_goals[0].remaining = 100
            return petition_goals[0]
        else:
            # Fallback to first goal if no petitions exist
            first_goal = self.game.level_state.goals[0]
            first_goal.remaining = 100
            return first_goal

    def test_bank_awards_gold(self):
        self.game.state_manager.transition_to_rolling()
        
        # Set up event collector FIRST, before any actions
        from farkle.core.game_event import GameEvent, GameEventType
        events = []
        def collect(e):
            events.append(e.type)
        self.game.event_listener.subscribe(collect)
        
        # Use an existing petition goal and give it a gold reward
        petition = None
        for goal in self.game.level_state.goals:
            if not goal.is_disaster:
                petition = goal
                break
        
        # If no petition exists, use the first goal (but this should be rare)
        if not petition:
            petition = self.game.level_state.goals[0]
        
        # Make it easy to fulfill and give it a gold reward
        petition.remaining = 100
        petition.reward_gold = 50
        petition.persona = "merchant"
        
        # Set as active goal
        self.game.active_goal_index = self.game.level_state.goals.index(petition)
        
        # Lock a die worth 100 points (single 1)
        die = self.game.dice[0]
        die.value = 1
        die.selected = True
        die.scoring_eligible = True
        self.assertTrue(self.game.selection_is_single_combo())
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        
        # Check pending score was accumulated
        self.assertGreater(petition.pending_raw, 0, f"Petition should have pending_raw > 0, got {petition.pending_raw}")
        
        prev_gold = self.game.player.gold
        expected_reward = petition.reward_gold
        self.assertTrue(handle_bank(self.game), "Banking should succeed")
        
        # Goal should now be fulfilled
        self.assertTrue(petition.is_fulfilled(), f"Goal should be fulfilled. Remaining: {petition.remaining}")
        
        # Check if GOAL_FULFILLED was published (it's emitted after TURN_END)
        self.assertIn(GameEventType.GOAL_FULFILLED, events, f"GOAL_FULFILLED should be in events: {events}")
        
        # Check gold was awarded
        self.assertEqual(self.game.player.gold, prev_gold + expected_reward, 
                        f"Gold should increase by {expected_reward} (petition reward). Was {prev_gold}, now {self.game.player.gold}")

    def test_hot_dice_reset(self):
        self.game.state_manager.transition_to_rolling()
        for d in self.game.dice:
            d.hold()
        handle_roll(self.game)
        self.assertFalse(all(d.held for d in self.game.dice), "Hot dice reset should release held state")
        self.assertFalse(self.game.locked_after_last_roll, "Lock-after-roll should reset after hot dice reset")

if __name__ == '__main__':
    unittest.main()
