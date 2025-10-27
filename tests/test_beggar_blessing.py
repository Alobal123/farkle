"""Test beggar blessing rewards."""
import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType
from farkle.goals.goal import Goal


class BeggarBlessingTests(unittest.TestCase):
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

    def test_beggar_grants_double_score_blessing(self):
        """When a beggar petition is fulfilled, player receives double score blessing."""
        # Create a beggar goal with blessing reward
        goal = Goal(
            target_score=100,
            game=self.game,
            name="Beggar's Prayer",
            is_disaster=False,
            reward_gold=0,
            reward_income=0,
            reward_blessing="double_score",
            persona="beggar"
        )
        
        # Fulfill the goal
        goal.subtract(100)
        self.assertTrue(goal.is_fulfilled())
        
        # Track active effects count before
        initial_effects = len(self.game.player.active_effects)
        
        # Emit GOAL_FULFILLED event
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal": goal}))
        
        # Player should have one more active effect (the blessing)
        self.assertEqual(len(self.game.player.active_effects), initial_effects + 1)
        
        # The effect should be a blessing
        blessing = self.game.player.active_effects[-1]
        self.assertEqual(blessing.name, "Divine Fortune")
        from farkle.core.effect_type import EffectType
        self.assertEqual(blessing.effect_type, EffectType.BLESSING)
        # Duration is 1 (lasts for next turn, decrements on TURN_START)
        self.assertEqual(blessing.duration, 1)

    def test_double_score_blessing_doubles_scores(self):
        """Double score blessing should double all scores."""
        # Create a beggar goal
        goal = Goal(
            target_score=100,
            game=self.game,
            name="Beggar's Prayer",
            is_disaster=False,
            reward_blessing="double_score",
            persona="beggar"
        )
        
        # Fulfill the goal to grant the blessing
        goal.subtract(100)
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal": goal}))
        
        # Verify blessing is active
        self.assertEqual(len(self.game.player.active_effects), 1)
        
        # Create a simple scoring scenario
        self.game.state_manager.transition_to_rolling()
        
        # Select a single 1 (worth 100 points normally)
        die = self.game.dice[0]
        die.value = 1
        die.selected = True
        die.scoring_eligible = True
        
        # Use the preview system to get the adjusted score
        raw, pending, adjusted, mult = self.game.selection_preview()
        
        # With the blessing, the score should be doubled (200 instead of 100)
        self.assertEqual(adjusted, 200)

    def test_blessing_expires_after_one_turn(self):
        """Double score blessing should last through the next full turn."""
        # Create and fulfill a beggar goal
        goal = Goal(
            target_score=100,
            game=self.game,
            name="Beggar's Prayer",
            is_disaster=False,
            reward_blessing="double_score",
            persona="beggar"
        )
        goal.subtract(100)
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal": goal}))
        
        # Verify blessing is active with duration 1
        self.assertEqual(len(self.game.player.active_effects), 1)
        blessing = self.game.player.active_effects[0]
        self.assertEqual(blessing.duration, 1)
        
        # TURN_START (start of next turn) - first one is skipped due to _skip_next_decrement
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={}))
        
        # Blessing should still be active (skip flag was consumed)
        self.assertEqual(len(self.game.player.active_effects), 1)
        self.assertEqual(blessing.duration, 1)
        
        # Second TURN_START - this actually decrements the blessing
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={}))
        
        # Blessing should now be removed
        self.assertEqual(len(self.game.player.active_effects), 0)


if __name__ == '__main__':
    unittest.main()
