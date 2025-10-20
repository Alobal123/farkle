import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType
from tests.test_utils import EventCollector

class RightClickAutoLockTests(unittest.TestCase):
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
        # Move to rolling state for die interaction
        self.game.state_manager.transition_to_rolling()
        # Configure first die as a guaranteed scoring single (value 1) eligible
        d = self.game.dice[0]
        d.value = 1
        d.scoring_eligible = True
        d.selected = False
        self.game.update_current_selection_score()

    def test_right_click_selects_and_locks_single_scoring_die(self):
        d = self.game.dice[0]
        self.assertFalse(d.selected)
        mx,my = d.x + 5, d.y + 5
        consumed = self.game._handle_die_click(mx, my, button=3)
        self.assertTrue(consumed, "Right-click handler should consume the event")
        self.assertTrue(d.held, "Die should be held after auto-lock")
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.DIE_SELECTED, types)
        self.assertIn(GameEventType.DIE_HELD, types)
        self.assertIn(GameEventType.TURN_LOCK_ADDED, types)
        self.assertGreater(self.game.turn_score, 0)

if __name__ == '__main__':
    unittest.main()
