import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEventType
from tests.test_utils import EventCollector

class RightClickBackgroundClearsSelectionTests(unittest.TestCase):
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
        # Select two dice to simulate a multi-die selection
        for i in (0,1):
            d = self.game.dice[i]
            d.value = 1
            d.scoring_eligible = True
            d.selected = True
        self.game.update_current_selection_score()

    def test_right_click_background_clears(self):
        # Choose coordinates far from any die (top-left corner padding)
        mx,my = 5,5
        # Simulate right-click by invoking run loop handler fragment directly
        # We call the event handler logic through _handle_die_click only when hitting dice; background clear is in run loop.
        # So we manually mimic the branch:
        die_hit = any((not d.held) and d.rect().collidepoint(mx,my) for d in self.game.dice)
        self.assertFalse(die_hit, "Coordinates should not hit a die for background clear test")
        # Invoke the new clear helper directly
        cleared = self.game.clear_all_selected_dice()
        self.assertTrue(cleared, "Expected to clear existing selection")
        types = [e.type for e in self.collector.events]
        # Expect DIE_DESELECTED for each previously selected die
        self.assertGreaterEqual(types.count(GameEventType.DIE_DESELECTED), 2)
        self.assertEqual(sum(1 for d in self.game.dice if d.selected), 0, "All dice should be deselected")

if __name__ == '__main__':
    unittest.main()
