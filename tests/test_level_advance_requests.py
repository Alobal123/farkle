import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class LevelAdvanceRequestTests(unittest.TestCase):
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

    def fulfill_level_and_advance(self):
        # Make first goal trivial
        goal = self.game.level_state.goals[0]
        goal.remaining = 50
        # Simulate rolling & locking a 1 worth 100 to fulfill
        self.game.state_manager.transition_to_rolling()
        d = self.game.dice[0]
        d.value = 1; d.selected = True; d.scoring_eligible = True
        self.game.update_current_selection_score()
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_LOCK))
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_BANK))
    # No polling needed; events synchronous. Advancement should occur automatically after TURN_END and LEVEL_COMPLETE.

    def test_can_roll_after_level_advances(self):
        self.fulfill_level_and_advance()
        # New level active, attempt first roll via request
        before_events = []
        class Collector:
            def __init__(self): self.events = []
            def on_event(self, e): self.events.append(e.type)
        collector = Collector()
        self.game.event_listener.subscribe(collector.on_event)
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        # Expect either TURN_ROLL (preferred) or at least PRE_ROLL sequence to indicate roll succeeded.
        self.assertTrue(any(ev in (GameEventType.TURN_ROLL, GameEventType.PRE_ROLL) for ev in collector.events),
                        "Roll lifecycle events should appear after level advance")

if __name__ == '__main__':
    unittest.main()
