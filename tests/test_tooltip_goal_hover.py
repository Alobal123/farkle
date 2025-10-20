import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.ui.tooltip import resolve_hover
from farkle.core.game_event import GameEvent, GameEventType

class TooltipGoalHoverTests(unittest.TestCase):
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
        # Force a draw so goal rects cached
        self.game.renderer.draw()
        pygame.display.flip()

    def test_goal_tooltip_shows_applied_and_remaining(self):
        goal = self.game.level_state.goals[0]
        rect = getattr(goal, '_last_rect', None)
        # Assert then guard to satisfy static analysis (rect could be None before first full draw)
        self.assertIsNotNone(rect, 'Goal rect should be cached after draw')
        if rect is None:
            # Fail safe: abort test early if draw pipeline changed
            return
        # Simulate locking 100 points to the goal (single five with modifier if any)
        # Directly publish LOCK event targeting goal index 0
        self.game.event_listener.publish(GameEvent(GameEventType.LOCK, payload={'goal_index':0,'points':100,'rule_key':'SingleValue:1'}))
        tip = resolve_hover(self.game, (rect.centerx, rect.centery))
        self.assertIsNotNone(tip, 'Tooltip should resolve for goal hover')
        lines = tip.get('lines', [])
        # Expect at least Remaining or Fulfilled line always present as first line
        self.assertTrue(lines, 'Tooltip lines should not be empty')
        self.assertTrue(any(ln.startswith('Remaining:') or ln.startswith('Fulfilled') for ln in lines), 'Should include Remaining: or Fulfilled status line')
        # Applied progress line now appears as part of status_parts prefixed with Applied:
        self.assertTrue(any('Applied:' in ln for ln in lines), f'Applied progress expected in lines: {lines}')

if __name__ == '__main__':
    unittest.main()
