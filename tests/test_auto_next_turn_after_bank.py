import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class AutoNextTurnAfterBankTests(unittest.TestCase):
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

    def test_auto_next_turn_after_bank_incomplete_level(self):
        # Roll to enter ROLLING state
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        # Create a scoring selection to allow banking: mark first die scoring + lock via right-click
        d0 = self.game.dice[0]
        d0.value = 1; d0.scoring_eligible = True; d0.selected = True
        self.game.update_current_selection_score()
        # Auto-lock scoring selection
        d_rect = d0.rect()
        self.game._handle_die_click(d_rect.x+2, d_rect.y+2, button=3)  # right-click lock
        # Bank
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BANK))
        # Ensure bank cycle events occurred
        self.assertIn(GameEventType.BANK, self._types())
        self.assertIn(GameEventType.TURN_BANKED, self._types())
        self.assertIn(GameEventType.TURN_END, self._types())
        # After TURN_END(bank), next turn should have begun automatically (PRE_ROLL + TURN_START)
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL', 'Should auto enter PRE_ROLL after banking')
        self.assertIn(GameEventType.TURN_START, self._types())

if __name__ == '__main__':
    unittest.main()
