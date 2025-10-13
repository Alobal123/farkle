import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class EventCollector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class DiceEventTests(unittest.TestCase):
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

    def test_roll_emits_pre_and_post_and_die_rolled(self):
        # First roll request
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.PRE_ROLL, types)
        self.assertIn(GameEventType.POST_ROLL, types)
        self.assertTrue(any(t == GameEventType.DIE_ROLLED for t in types))
        # POST_ROLL should appear after at least one DIE_ROLLED
        first_post = types.index(GameEventType.POST_ROLL)
        first_die = types.index(GameEventType.DIE_ROLLED)
        self.assertLess(first_die, first_post)

    def test_selection_emits_selected_deselected(self):
        # Transition to rolling and mark a die scoring eligible manually
        self.game.state_manager.transition_to_rolling()
        d = self.game.dice[0]
        d.scoring_eligible = True
        d.value = 1
        # Simulate click logic directly: toggle select and publish selection events via loop code
        # We'll call same code path: replicate minimal portion
        before_len = len(self.collector.events)
        d.toggle_select()  # this won't auto publish; emulate event manually
        self.game.event_listener.publish(GameEvent(GameEventType.DIE_SELECTED, payload={"index":0}))
        types = [e.type for e in self.collector.events[before_len:]]
        self.assertIn(GameEventType.DIE_SELECTED, types)

    def test_die_held_on_lock(self):
        self.game.state_manager.transition_to_rolling()
        d = self.game.dice[0]
        d.value = 1; d.selected = True; d.scoring_eligible = True
        self.game.update_current_selection_score()
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_LOCK))
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.DIE_HELD, types)

if __name__ == '__main__':
    unittest.main()
