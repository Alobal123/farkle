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
        # Find a petition goal (not disaster) since disasters have no rewards
        petition_goals = [g for g in self.game.level_state.goals if not g.is_disaster and g.reward_gold > 0]
        if petition_goals:
            # Make the first petition goal easy and set as active
            petition_goals[0].remaining = 100
            self.game.active_goal_index = self.game.level_state.goals.index(petition_goals[0])
        else:
            # Fallback: make first goal easy
            self.game.level_state.goals[0].remaining = 100
        self.collector = Collector()
        self.game.event_listener.subscribe(self.collector.on_event)

    def test_goal_fulfilled_and_gold_events(self):
        # Verify we have a petition goal with rewards
        petition_goals = [g for g in self.game.level_state.goals if not g.is_disaster and g.reward_gold > 0]
        if not petition_goals:
            self.skipTest("No petition goals with rewards available")
        
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