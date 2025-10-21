import unittest, pygame, random
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class FarkleFailedRescueRerollTests(unittest.TestCase):
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

    def test_failed_rescue_keeps_farkle_and_next_button(self):
        # Roll once then force farkle
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        pattern = [2,3,4,6,2,3]
        for i,d in enumerate(self.game.dice):
            d.value = pattern[i]
            d.selected = False
            d.scoring_eligible = False
            d.held = False
        self.game.mark_scoring_dice(); self.assertTrue(self.game.check_farkle())
        self.game.state_manager.transition_to_farkle()
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        # Enter reroll selection
        reroll = self.game.ability_manager.get('reroll'); self.assertIsNotNone(reroll)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
        reroll = self.game.ability_manager.get('reroll')
        self.assertTrue(reroll and reroll.selecting)
        # Monkeypatch randomness to avoid scoring (always 2)
        original_randint = random.randint
        random.randint = lambda a,b: 2
        try:
            target_index = next(i for i,d in enumerate(self.game.dice) if not d.held)
            self.assertTrue(self.game.ability_manager.attempt_target('die', target_index))
            self.assertTrue(self.game.ability_manager.finalize_selection())
        finally:
            random.randint = original_randint
        # State should remain FARKLE, message indicates persistence
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        self.assertIn('farkle persists', self.game.message.lower())
        # Next button should be visible/enabled
        next_btn = next((b for b in self.game.ui_buttons if b.name == 'next'), None)
        self.assertIsNotNone(next_btn)
        self.assertTrue(next_btn.is_enabled_fn(self.game))

if __name__ == '__main__':
    unittest.main()