import unittest, pygame, random
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class FailedRescueNextTurnTests(unittest.TestCase):
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

    def _types(self):
        return [e.type for e in self.collector.events]

    def test_next_turn_after_failed_rescue(self):
        # 1. Enter ROLLING by initial roll
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')
        # 2. Force a farkle pattern
        pattern = [2,3,4,6,2,3]
        for i,d in enumerate(self.game.dice):
            d.value = pattern[i]; d.selected=False; d.scoring_eligible=False; d.held=False
        self.game.mark_scoring_dice(); self.assertTrue(self.game.check_farkle())
        self.game.state_manager.transition_to_farkle()
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        # 3. Activate reroll ability and force non-scoring reroll result (e.g., reroll a die to 2)
        reroll = self.game.ability_manager.get('reroll'); self.assertIsNotNone(reroll)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
        reroll = self.game.ability_manager.get('reroll'); self.assertTrue(reroll and reroll.selecting)
        original_randint = random.randint; random.randint = lambda a,b: 2
        try:
            target_index = next(i for i,d in enumerate(self.game.dice) if not d.held)
            self.assertTrue(self.game.ability_manager.attempt_target('die', target_index))
            # Confirm still selecting before finalize
            self.assertEqual(self.game.state_manager.get_state().name, 'SELECTING_TARGETS')
            # Finalize selection (right-click simulation)
            self.assertTrue(self.game.ability_manager.finalize_selection())
        finally:
            random.randint = original_randint
        # 4. Confirm still FARKLE (failed rescue)
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE')
        # 5. Emit REQUEST_NEXT_TURN and expect PRE_ROLL state and TURN_START event
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_NEXT_TURN))
        self.assertEqual(self.game.state_manager.get_state().name, 'PRE_ROLL', 'Next Turn should reset to PRE_ROLL')
        self.assertIn(GameEventType.TURN_START, self._types())

if __name__ == '__main__':
    unittest.main()
