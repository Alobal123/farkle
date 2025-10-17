import unittest
import pygame
from game import Game
from settings import WIDTH, HEIGHT

class GameLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        # Hidden window to avoid UI popups during tests
        flags = 0
        if hasattr(pygame, 'HIDDEN'):
            flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)
        # Force into ROLLING state for most selection tests
        self.game.state_manager.transition_to_rolling()
        # Ensure no randomness interference
        for d in self.game.dice:
            d.selected = False
            d.held = False
            d.scoring_eligible = False

    def _select_values(self, values):
        """Helper: assign given values to first dice and select them."""
        for i, val in enumerate(values):
            self.game.dice[i].value = val
            self.game.dice[i].selected = True
            self.game.dice[i].scoring_eligible = True  # mark as scoring for simplicity
        # Non-selected dice set to innocuous value
        for j in range(len(values), len(self.game.dice)):
            self.game.dice[j].value = 2
            self.game.dice[j].selected = False
            self.game.dice[j].scoring_eligible = False
        self.game.update_current_selection_score()

    def test_single_value_combo(self):
        self._select_values([1])
        self.assertTrue(self.game.selection_is_single_combo())
        self.assertGreater(self.game.current_roll_score, 0)

    def test_two_single_values_not_single_combo(self):
        self._select_values([1, 5])
        self.assertFalse(self.game.selection_is_single_combo())
        # current_roll_score should be zero because not a single combo
        self.assertEqual(self.game.current_roll_score, 0)

    def test_three_of_a_kind_combo(self):
        self._select_values([2, 2, 2])
        self.assertTrue(self.game.selection_is_single_combo())
        self.assertGreater(self.game.current_roll_score, 0)

    def test_mixed_triple_and_single_invalid(self):
        self._select_values([3, 3, 3, 5])
        self.assertFalse(self.game.selection_is_single_combo())
        self.assertEqual(self.game.current_roll_score, 0)

    def test_button_states_pre_roll(self):
        fresh_game = Game(self.screen, self.font, self.clock)
        # Fresh game should be in PRE_ROLL
        states = {b.name: b.is_enabled_fn(fresh_game) for b in fresh_game.ui_buttons}
        self.assertTrue(states['roll'])
        self.assertFalse(states['bank'])

    def test_button_states_valid_selection(self):
        self._select_values([1])
        states = {b.name: b.is_enabled_fn(self.game) for b in self.game.ui_buttons}
        self.assertTrue(states['bank'])  # valid combo allows banking
        # roll allowed because valid combo present even if not yet locked
        self.assertTrue(states['roll'])

    def test_button_states_after_lock(self):
        # Simulate locked combo (turn_score > 0, no selection)
        self.game.turn_score = 100
        self.game.locked_after_last_roll = True
        for d in self.game.dice:
            d.selected = False
        states = {b.name: b.is_enabled_fn(self.game) for b in self.game.ui_buttons}
        self.assertTrue(states['roll'])  # can roll after locking
        self.assertTrue(states['bank'])  # can bank accumulated turn score

if __name__ == '__main__':
    unittest.main()
