"""Test that different personas give different rewards."""
import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType
from farkle.level.level import Level
from farkle.core.random_source import RandomSource

class PersonaRewardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'):
            flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)

    def test_merchant_gives_gold(self):
        """Merchant petitions should give gold rewards."""
        # Create a level with a specific seed to get predictable petitions
        rng = RandomSource(seed=123)
        level = Level.single("Test", 300, 3, "Test level", rng=rng)
        
        # Check if any goals are merchant petitions and have gold rewards
        merchant_goals = [goal for goal in level.goals 
                         if len(goal) >= 8 and goal[7] == 'merchant']
        
        if merchant_goals:
            # Merchant goals should have gold reward (index 3) > 0
            for goal in merchant_goals:
                self.assertGreater(goal[3], 0, "Merchant petition should give gold reward")
                self.assertEqual(goal[4], 0, "Merchant petition should not give income reward")

    def test_nobleman_gives_income(self):
        """Nobleman petitions should give income rewards."""
        # Create a level with a specific seed to get predictable petitions
        rng = RandomSource(seed=456)
        level = Level.single("Test", 300, 3, "Test level", rng=rng)
        
        # Check if any goals are nobleman petitions and have income rewards
        nobleman_goals = [goal for goal in level.goals 
                         if len(goal) >= 8 and goal[7] == 'nobleman']
        
        if nobleman_goals:
            # Nobleman goals should have income reward (index 4) == 5
            for goal in nobleman_goals:
                self.assertEqual(goal[3], 0, "Nobleman petition should not give gold reward")
                self.assertEqual(goal[4], 5, "Nobleman petition should give +5 income reward")

    def test_income_reward_increases_temple_income(self):
        """When a goal with income reward is fulfilled, temple income should increase."""
        # Manually create a goal with income reward
        from farkle.goals.goal import Goal
        goal = Goal(target_score=100, name="Test Income", is_disaster=False, 
                   reward_gold=0, reward_income=5, persona="nobleman")
        
        # Subscribe to game
        goal.game = self.game
        self.game.level_state.goals.append(goal)
        
        initial_income = self.game.player.temple_income
        
        # Fulfill the goal
        goal.subtract(100)
        self.assertTrue(goal.is_fulfilled())
        
        # Emit GOAL_FULFILLED event
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal": goal}))
        
        # Check that temple income increased
        self.assertEqual(self.game.player.temple_income, initial_income + 5)

    def test_gold_reward_increases_gold(self):
        """When a goal with gold reward is fulfilled, gold should increase."""
        from farkle.goals.goal import Goal
        goal = Goal(target_score=100, name="Test Gold", is_disaster=False, 
                   reward_gold=50, reward_income=0, persona="merchant")
        
        # Subscribe to game
        goal.game = self.game
        self.game.level_state.goals.append(goal)
        
        initial_gold = self.game.player.gold
        
        # Fulfill the goal
        goal.subtract(100)
        self.assertTrue(goal.is_fulfilled())
        
        # Emit GOAL_FULFILLED event
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal": goal}))
        
        # Check that gold increased
        self.assertEqual(self.game.player.gold, initial_gold + 50)

    def test_income_gained_event_published(self):
        """When income reward is gained, INCOME_GAINED event should be published."""
        from farkle.goals.goal import Goal
        
        # Track events
        events_received = []
        def event_handler(event):
            if event.type == GameEventType.INCOME_GAINED:
                events_received.append(event)
        
        # Subscribe to events (callback first, then event types)
        self.game.event_listener.subscribe(event_handler, [GameEventType.INCOME_GAINED])
        
        goal = Goal(target_score=100, name="Test Income Event", is_disaster=False, 
                   reward_gold=0, reward_income=5, persona="nobleman")
        
        goal.game = self.game
        self.game.level_state.goals.append(goal)
        
        # Fulfill the goal
        goal.subtract(100)
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal": goal}))
        
        # Check that INCOME_GAINED event was published
        self.assertEqual(len(events_received), 1)
        event = events_received[0]
        self.assertEqual(event.get("amount"), 5)
        self.assertEqual(event.get("goal_name"), "Test Income Event")
        self.assertEqual(event.get("new_total"), 35)  # 30 starting + 5 gained

if __name__ == '__main__':
    unittest.main()
