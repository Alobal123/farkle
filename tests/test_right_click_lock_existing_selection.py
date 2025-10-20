import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType
from tests.test_utils import EventCollector

class RightClickExistingSelectionLockTests(unittest.TestCase):
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
        # Configure first die as scoring eligible
        d = self.game.dice[0]
        d.value = 1
        d.scoring_eligible = True
        d.selected = True  # already selected before right-click
        # Mark current selection score
        self.game.update_current_selection_score()

    def test_right_click_on_already_selected_scoring_die_locks(self):
        d = self.game.dice[0]
        mx,my = d.x + 5, d.y + 5
        consumed = self.game._handle_die_click(mx, my, button=3)
        self.assertTrue(consumed)
        self.assertTrue(d.held, "Die should be held after lock")
        types = [e.type for e in self.collector.events]
        # Should not emit a second DIE_SELECTED for the already selected die
        self.assertEqual(types.count(GameEventType.DIE_SELECTED), 0, "No new DIE_SELECTED event expected")
        self.assertIn(GameEventType.DIE_HELD, types)
        self.assertIn(GameEventType.TURN_LOCK_ADDED, types)
        self.assertGreater(self.game.turn_score, 0)

if __name__ == '__main__':
    unittest.main()
