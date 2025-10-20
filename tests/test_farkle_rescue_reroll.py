import unittest, pygame, random
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class FarkleRescueRerollTests(unittest.TestCase):
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

    def test_farkle_rescued_by_reroll(self):
        # 1. Roll once to leave PRE_ROLL.
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')
        # 2. Manually force FARKLE state with a non-scoring pattern
        pattern = [2,3,4,6,2,3]
        for i, d in enumerate(self.game.dice):
            d.value = pattern[i]
            d.selected = False
            d.scoring_eligible = False
            d.held = False
        self.game.mark_scoring_dice(); self.assertTrue(self.game.check_farkle())
        self.game.state_manager.transition_to_farkle()
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        # 4. Activate reroll ability selection.
        reroll = self.game.ability_manager.get('reroll')
        self.assertIsNotNone(reroll)
        self.assertGreater(reroll.available(), 0)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
        reroll = self.game.ability_manager.get('reroll')
        self.assertTrue(reroll and reroll.selecting)
        # 5. Monkeypatch randomness so rerolled die becomes scoring (1) rescuing the farkle.
        original_randint = random.randint
        random.randint = lambda a,b: 1
        try:
            target_index = next(i for i,d in enumerate(self.game.dice) if not d.held)
            # Use ability manager targeting to ensure selecting state exits properly
            self.assertTrue(self.game.ability_manager.attempt_target('die', target_index))
        finally:
            random.randint = original_randint
        # 6. After reroll, selecting state should have exited and game returned to ROLLING via rescue.
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING', 'Farkle should be rescued to ROLLING')
        self.assertIn(GameEventType.REROLL, self._types())
    # Message may be overridden by later UI logic; rely on state & REROLL event for success.

if __name__ == '__main__':
    unittest.main()
