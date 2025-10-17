import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEventType
from tests.test_utils import EventCollector

class RightClickSelectedInvalidComboTests(unittest.TestCase):
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
        self.collector = EventCollector()
        self.game.event_listener.subscribe(self.collector.on_event)
        self.game.state_manager.transition_to_rolling()
        # Configure two dice such that selecting both does NOT form a single scoring combo per rules
        # We assume a lone '1' scores; two different singles (1 and 5) together may not be a single combo.
        d0 = self.game.dice[0]; d1 = self.game.dice[1]
        d0.value = 1; d1.value = 5
        for d in (d0,d1):
            d.scoring_eligible = True
            d.selected = True
        # Update current selection score (should reset because multi selection not single combo)
        self.game.update_current_selection_score()

    def test_right_click_on_selected_invalid_combo_does_not_lock(self):
        d0 = self.game.dice[0]
        mx,my = d0.x + 5, d0.y + 5
        consumed = self.game._handle_die_click(mx, my, button=3)
        self.assertTrue(consumed)
        # Expect not held because selection is not a single valid combo
        self.assertFalse(d0.held, "First die should remain unheld")
        self.assertFalse(self.game.dice[1].held, "Second die should remain unheld")
        types = [e.type for e in self.collector.events]
        # No TURN_LOCK_ADDED event expected
        self.assertNotIn(GameEventType.TURN_LOCK_ADDED, types)
        # Ensure no DIE_DESELECTED rollback occurred (selection stays as-is)
        self.assertEqual(types.count(GameEventType.DIE_DESELECTED), 0)

if __name__ == '__main__':
    unittest.main()
