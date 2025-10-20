import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType, GameEvent

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class TurnEventTests(unittest.TestCase):
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
        self.collector = Collector()
        self.game.event_listener.subscribe(self.collector.on_event)

    def _types(self):
        return [e.type for e in self.collector.events]

    def test_roll_lock_bank_sequence(self):
        # Roll
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        # Ensure TURN_ROLL appeared
        self.assertIn(GameEventType.TURN_ROLL, self._types())
        # Fake make a scoring selection to allow lock
        d = self.game.dice[0]; d.scoring_eligible = True; d.selected = True; d.value = 1
        self.game.update_current_selection_score()
        # Right-click auto-lock the selected scoring die
        d_rect = self.game.dice[0].rect()
        self.game._handle_die_click(d_rect.x+2, d_rect.y+2, button=3)
        self.assertIn(GameEventType.TURN_LOCK_ADDED, self._types())
        # Bank (after selection auto-lock if not already)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BANK))
        self.assertIn(GameEventType.TURN_BANKED, self._types())
        self.assertIn(GameEventType.TURN_END, self._types())

if __name__ == '__main__':
    unittest.main()
