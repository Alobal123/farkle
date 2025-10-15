import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class EventCollector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class RerollAbilityTests(unittest.TestCase):
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

    def _types(self):
        return [e.type for e in self.collector.events]

    def test_reroll_single_use_decrements(self):
        remaining_before = self.game.rerolls_remaining()
        # Perform initial roll (required before reroll now)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        # Enter selection mode after first roll
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
        self.assertTrue(self.game.reroll_selecting)
        # Target first non-held die
        self.game.use_reroll_on_die(0)
        self.assertIn(GameEventType.REROLL, self._types())
        self.assertEqual(self.game.rerolls_remaining(), remaining_before - 1)
        # Try to enter selection again (should deny and not consume more)
        before_events = self._types().count(GameEventType.REROLL)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
        self.assertEqual(self._types().count(GameEventType.REROLL), before_events)

    def test_reroll_after_farkle_defers_turn_end(self):
        # Force a farkle state with no scoring dice (set all values to non-scoring pattern e.g., 2,3,4,6,2,3)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        # Create an initial scoring lock so turn_score > 0
        d0 = self.game.dice[0]
        d0.value = 1; d0.selected = True; d0.scoring_eligible = True
        self.game.update_current_selection_score()
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        self.assertGreater(self.game.turn_score, 0)
        # Now set remaining (unheld) dice to farkle pattern
        pattern = [2,3,4,6,2,3]
        for d in self.game.dice:
            if not d.held:
                d.value = pattern.pop(0)
                d.selected = False
                d.scoring_eligible = False
        self.game.mark_scoring_dice()
        self.assertTrue(self.game.check_farkle())
        self.game.locked_after_last_roll = True  # satisfy roll guard
        # Monkeypatch roll to avoid altering dice so we keep farkle pattern
        original_roll = self.game.dice_container.roll
        self.game.dice_container.roll = lambda : None
        try:
            self.game.handle_roll()
        finally:
            self.game.dice_container.roll = original_roll
        self.assertIn(GameEventType.FARKLE, self._types())
        # TURN_END not yet emitted (deferred)
        self.assertNotIn(GameEventType.TURN_END, [e.type for e in self.collector.events if e.type == GameEventType.TURN_END])
        # Use reroll
        if self.game.rerolls_remaining() > 0:
            self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
            self.assertTrue(self.game.reroll_selecting)
            # Reroll an unheld die
            target_index = next(i for i,d in enumerate(self.game.dice) if not d.held)
            self.game.use_reroll_on_die(target_index)
            self.assertIn(GameEventType.REROLL, self._types())

if __name__ == '__main__':
    unittest.main()
