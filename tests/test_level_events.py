import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEventType, GameEvent

class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, e):
        self.events.append(e)

class LevelEventTests(unittest.TestCase):
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

    def test_level_complete_sequence(self):
        # Simulate completing the only mandatory goal by locking then banking enough points.
        # Force dice into a three-of-a-kind of ones (1000) to surpass target (300 default).
        for i, d in enumerate(self.game.dice[:3]):
            d.value = 1
            d.selected = True
            d.scoring_eligible = True
        # Mark remaining dice as non-scoring to keep selection single combo
        for d in self.game.dice[3:]:
            d.value = 2
            d.selected = False
            d.scoring_eligible = False
        self.game.update_current_selection_score()
        # Lock selection
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_LOCK))
        # Bank to apply progress and trigger completion
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BANK))
    # No polling: advancement should happen automatically after TURN_END + completion
    # Allow event chain to process (no real loop, events synchronous)
        types = self._types()
        # Assertions
        self.assertIn(GameEventType.LEVEL_COMPLETE, types)
        self.assertIn(GameEventType.TURN_END, types)
        self.assertIn(GameEventType.LEVEL_ADVANCE_STARTED, types)
        self.assertIn(GameEventType.LEVEL_GENERATED, types)
        # New TURN_START for next level should appear after LEVEL_GENERATED
        gen_idx = types.index(GameEventType.LEVEL_GENERATED)
        later_turn_starts = [i for i,t in enumerate(types) if t == GameEventType.TURN_START and i > gen_idx]
        self.assertTrue(later_turn_starts, "Expected TURN_START after LEVEL_GENERATED for new level")

if __name__ == '__main__':
    unittest.main()
