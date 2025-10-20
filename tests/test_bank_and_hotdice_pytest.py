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
        self.game = Game(self.screen, self.font, self.clock)

    def make_goal_easy(self):
        first_goal = self.game.level_state.goals[0]
        first_goal.remaining = 100

    def test_bank_awards_gold(self):
        self.game.state_manager.transition_to_rolling()
        self.make_goal_easy()
        die = self.game.dice[0]
        die.value = 1
        die.selected = True
        die.scoring_eligible = True
        self.assertTrue(self.game.selection_is_single_combo())
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        prev_gold = self.game.player.gold
        handle_bank(self.game)
        self.assertGreater(self.game.player.gold, prev_gold, "Gold should increase on fulfilled goal banking")

    def test_hot_dice_reset(self):
        self.game.state_manager.transition_to_rolling()
        for d in self.game.dice:
            d.hold()
        handle_roll(self.game)
        self.assertFalse(all(d.held for d in self.game.dice), "Hot dice reset should release held state")
        self.assertFalse(self.game.locked_after_last_roll, "Lock-after-roll should reset after hot dice reset")

if __name__ == '__main__':
    unittest.main()
