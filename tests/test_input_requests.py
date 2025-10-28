import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, event):
        self.events.append(event.type)

class InputRequestTests(unittest.TestCase):
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
        self.collector = Collector()
        self.game.event_listener.subscribe(self.collector.on_event)

    def test_roll_request_denied_without_lock_after_roll(self):
        # Start: first roll allowed
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertIn(GameEventType.ROLL, self.collector.events)
        # Try rolling again without a lock or valid selection
        before_count = self.collector.events.count(GameEventType.ROLL)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertEqual(before_count, self.collector.events.count(GameEventType.ROLL), "Second roll should be denied")
        self.assertIn(GameEventType.REQUEST_DENIED, self.collector.events)

    def test_right_click_generates_lock_event(self):
        # Prepare a scoring die (value 1) and select it then right-click to lock
        self.game.state_manager.transition_to_rolling()
        d = self.game.dice[0]
        d.value = 1; d.selected = True; d.scoring_eligible = True
        self.game.update_current_selection_score()
        rect = d.rect()
        self.game._handle_die_click(rect.x+3, rect.y+3, button=3)
        self.assertIn(GameEventType.LOCK, self.collector.events)

if __name__ == '__main__':
    unittest.main()
