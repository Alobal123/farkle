import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType

class EventCollector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class LeftClickSelectionUnifiedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)
        self.collector = EventCollector()
        self.game.event_listener.subscribe(self.collector.on_event)
        self.game.state_manager.transition_to_rolling()
        # Prepare scoring eligible first die
        d = self.game.dice[0]
        d.value = 1
        d.scoring_eligible = True
        d.selected = False

    def test_left_click_select_and_deselect(self):
        d = self.game.dice[0]
        mx,my = d.x + 5, d.y + 5
        consumed_select = self.game._handle_die_click(mx, my, button=1)
        self.assertTrue(consumed_select)
        self.assertTrue(d.selected)
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.DIE_SELECTED, types)
        # Deselect
        consumed_deselect = self.game._handle_die_click(mx, my, button=1)
        self.assertTrue(consumed_deselect)
        self.assertFalse(d.selected)
        types2 = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.DIE_DESELECTED, types2)

if __name__ == '__main__':
    unittest.main()
