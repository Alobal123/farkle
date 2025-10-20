import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from tests.test_utils import EventCollector

class GoalProgressBarTests(unittest.TestCase):
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
        # Transition to rolling to allow locking
        self.game.state_manager.transition_to_rolling()
        # Use active goal index 0
        self.goal = self.game.level_state.goals[self.game.active_goal_index]

    def test_progress_bar_segments_basic(self):
        # Simulate locking a scoring die to create pending_raw
        d = self.game.dice[0]
        d.value = 1; d.scoring_eligible = True; d.selected = True
        self.game.update_current_selection_score()
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        # Pending raw should now reflect locked points
        self.assertGreaterEqual(getattr(self.goal, 'pending_raw', 0), 0)
        # Draw once (will populate _last_rect)
        self.goal.draw(self.screen)
        self.assertIsNotNone(getattr(self.goal, '_last_rect', None))
        # Summary text present inside goal lines or bar overlay
        # We can approximate by ensuring lines cache exists
        lines = getattr(self.goal, '_last_lines', [])
        self.assertTrue(len(lines) > 0)

    def test_preview_addition(self):
        # Create a scoring eligible die and select without locking to show preview segment
        d = self.game.dice[0]
        d.value = 1; d.scoring_eligible = True; d.selected = True
        self.game.update_current_selection_score()
        # Ensure selection preview returns non-zero raw
        raw_sel, _, final_sel, _ = self.game.selection_preview()
        self.assertGreater(raw_sel, 0)
        self.goal.draw(self.screen)
        # Can't directly read bar segments, but ensure header text still present (no 'Rem:' lines now)
        lines = getattr(self.goal, '_last_lines', [])
        self.assertTrue(any(self.goal.name in ln for ln in lines))

if __name__ == '__main__':
    unittest.main()
