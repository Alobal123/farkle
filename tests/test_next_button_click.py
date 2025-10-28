import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class NextButtonClickTests(unittest.TestCase):
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
        # Enter FARKLE state
        self.game.state_manager.transition_to_farkle()
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        self.game.draw()

    def test_next_button_click_resets_turn_and_forfeits_rescue_if_available(self):
        # Button appears on any FARKLE now.
        next_btn = next((b for b in self.game.ui_buttons if b.name == 'next'), None)
        self.assertIsNotNone(next_btn, 'Next button should appear during FARKLE regardless of rescue availability')
        assert next_btn is not None
        mx, my = next_btn.rect.center
        handled = self.game.renderer.handle_click(self.game, (mx, my))
        self.assertTrue(handled, 'Renderer should consume next button click')
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL')
        types = [e.type for e in self.collector.events]
        self.assertIn(GameEventType.REQUEST_NEXT_TURN, types)
        # If rescue was available, expect a TURN_END(farkle_forfeit) prior to TURN_START
        # Collect TURN_END reasons
        turn_end_events = [e for e in self.collector.events if e.type == GameEventType.TURN_END]
        if turn_end_events:
            reasons = [e.payload.get('reason') for e in turn_end_events if hasattr(e, 'payload')]
            self.assertIn('farkle_forfeit', reasons)
        self.assertIn(GameEventType.TURN_START, types)

if __name__ == '__main__':
    unittest.main()