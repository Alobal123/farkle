import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEventType
from farkle.core.actions import handle_bank

class Collector(GameObject):
    def __init__(self):
        super().__init__("Collector")
        self.events: list = []
    def draw(self, surface):
        return
    def on_event(self, event):  # type: ignore[override]
        self.events.append(event.type)

class EventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)
        
        # Modify the first goal to have gold reward
        first_goal = self.game.level_state.goals[0]
        first_goal.remaining = 100
        first_goal.reward_gold = 50
        first_goal.is_disaster = False
        
        # Set it as the active goal
        self.game.active_goal_index = 0
        
        self.collector = Collector()
        self.game.event_listener.subscribe(self.collector.on_event)

    def test_goal_fulfilled_and_gold_events(self):
        # Simulate locking a single scoring die (1) worth 100
        die = self.game.dice[0]
        die.value = 1
        die.selected = True
        die.scoring_eligible = True
        self.game.state_manager.transition_to_rolling()
        # Force auto-lock to accumulate pending score
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        # Bank
        handle_bank(self.game)
        self.assertIn(GameEventType.GOAL_FULFILLED, self.collector.events)
        self.assertIn(GameEventType.GOLD_GAINED, self.collector.events)

if __name__ == '__main__':
    unittest.main()