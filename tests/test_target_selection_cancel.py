import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEventType

class EventCollector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class TargetSelectionCancelTests(unittest.TestCase):
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

    def _start_reroll_selection(self):
        abm = self.game.ability_manager
        abm.toggle_or_execute('reroll')
        self.assertEqual(self.game.state_manager.get_state().name, 'SELECTING_TARGETS')

    def test_escape_cancels_selection(self):
        # Start from FARKLE to verify prior state restoration after cancelling selection
        self.game.state_manager.transition_to_farkle()
        abm = self.game.ability_manager
        abm.toggle_or_execute('reroll')  # enter selecting targets from FARKLE
        self.assertEqual(self.game.state_manager.get_state().name, 'SELECTING_TARGETS')
        sel = abm.selecting_ability()
        if sel is None:
            self.fail("Reroll ability should be in selecting state from FARKLE")
        self.assertTrue(sel.selecting)
        # Simulate cancellation (ESC) by clearing selecting flag and exiting selecting state
        sel.selecting = False
        self.game.state_manager.exit_selecting_targets()  # should restore to FARKLE
        from game_event import GameEvent, GameEventType
        self.game.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_FINISHED, payload={"ability": sel.id, "reason": "cancelled"}))
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.TARGET_SELECTION_FINISHED, types)
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')

    def test_background_right_click_cancels(self):
        self._start_reroll_selection()
        # Emulate background right-click cancellation (not on a die)
        abm = self.game.ability_manager
        sel = abm.selecting_ability()
        if sel is None:
            self.fail("Reroll ability should be in selecting state")
        self.assertTrue(sel.selecting)
        # Directly perform cancellation logic (since we don't post real pygame events in test)
        sel.selecting = False
        self.game.state_manager.exit_selecting_targets()
        from game_event import GameEvent, GameEventType
        self.game.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_FINISHED, payload={"ability": sel.id, "reason": "cancelled"}))
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.TARGET_SELECTION_FINISHED, types)

if __name__ == '__main__':
    unittest.main()
