import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class NextButtonNoRescueTests(unittest.TestCase):
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
        # Exhaust reroll ability explicitly
        abm = getattr(self.game, 'ability_manager', None)
        reroll = abm.get('reroll') if abm else None
        if reroll:
            reroll.charges_used = reroll.charges_per_level
        self.game.state_manager.transition_to_farkle()
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        self.game.draw()

    def test_next_button_click_when_no_rescue_emits_no_forfeit_turn_end(self):
        next_btn = next((b for b in self.game.ui_buttons if b.name == 'next'), None)
        self.assertIsNotNone(next_btn)
        assert next_btn is not None
        mx, my = next_btn.rect.center
        handled = self.game.renderer.handle_click(self.game, (mx, my))
        self.assertTrue(handled)
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL')
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.REQUEST_NEXT_TURN, types)
        # TURN_END with reason farkle_forfeit should NOT appear (no rescue was possible)
        forfeits = [e for e in self.collector.events if e.type == GameEventType.TURN_END and getattr(e, 'payload', {}).get('reason') == 'farkle_forfeit']
        self.assertEqual(len(forfeits), 0)
        self.assertIn(GameEventType.TURN_START, types)

if __name__ == '__main__':
    unittest.main()