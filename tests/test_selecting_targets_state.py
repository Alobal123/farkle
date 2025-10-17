import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType
from tests.test_utils import EventCollector

class SelectingTargetsStateTests(unittest.TestCase):
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
        # Enter rolling state (needed for reroll ability activation)
        self.game.state_manager.transition_to_rolling()

    def test_enter_and_exit_selecting_targets(self):
        # Activate reroll ability (should enter selecting targets state)
        abm = self.game.ability_manager
        reroll = abm.get('reroll')
        self.assertIsNotNone(reroll, "Reroll ability should be registered by default")
        if reroll is None:
            return
        self.assertTrue(reroll.can_activate(abm), "Reroll should be activatable in rolling state")
        abm.toggle_or_execute('reroll')  # start selecting
        self.assertEqual(self.game.state_manager.get_state().name, 'SELECTING_TARGETS')
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.TARGET_SELECTION_STARTED, types)
        # Provide a die target to execute ability
        # choose first unheld die
        target_index = 0
        abm.attempt_target('die', target_index)
        self.assertIn(GameEventType.TARGET_SELECTION_FINISHED, [e.type for e in self.collector.events])
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')

if __name__ == '__main__':
    unittest.main()
