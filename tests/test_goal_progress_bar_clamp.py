import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT

class GoalProgressBarClampTests(unittest.TestCase):
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
        # Force initial draw to layout goals
        self.game.renderer.draw()
        pygame.display.flip()

    def test_progress_bar_segments_never_exceed_width(self):
        goal = self.game.level_state.goals[0]
        # Artificially inflate values beyond target to simulate overflow scenario
        goal.remaining = max(0, goal.target_score - goal.target_score - 200)  # so applied > target
        goal.pending_raw = 5000  # huge pending
        # Force preview addition via game.selection_preview: we can monkey patch selection preview logic
        # Instead directly simulate via temporary attribute used in draw calculation
        # Trigger draw (renderer invokes goal.draw); call twice to ensure updated state
        self.game.renderer.draw()
        goal.draw(self.screen)  # direct draw to ensure _last_bar_widths set
        pygame.display.flip()
        widths = getattr(goal, '_last_bar_widths', None)
        self.assertIsNotNone(widths, 'Expected debug bar widths dict after draw')
        if widths is None:
            return  # graceful early exit if not populated
        total_w = widths['total']
        sum_segments = widths['applied'] + widths['pending'] + widths['preview']
        self.assertLessEqual(sum_segments, total_w, f'Segments should not exceed total width: {sum_segments} > {total_w}')
        # Applied should be capped at total if overflow
        self.assertLessEqual(widths['applied'], total_w)
        # Pending/preview zeroed or reduced if overflow occurred
        self.assertLessEqual(widths['pending'], total_w - widths['applied'])
        self.assertLessEqual(widths['preview'], total_w - widths['applied'] - widths['pending'])

if __name__ == '__main__':
    unittest.main()
