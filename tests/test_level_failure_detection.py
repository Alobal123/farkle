"""Test that level failure is properly detected when running out of turns."""
import unittest
import pygame
from farkle.game import Game
from farkle.level.level import Level
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT

class LevelFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        # Create a level with only 1 turn to make failure easy to test
        self.level = Level.single(name="Test Level", target_goal=500, max_turns=1, reward_gold=100)
        self.game = Game(self.screen, self.font, self.clock, level=self.level, rng_seed=42)
        
        # Capture events
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))

    def test_failure_detected_on_last_turn(self):
        """Test that LEVEL_FAILED is emitted when banking on the last turn without completing goals."""
        # Ensure we're on turn 1 with 1 turn total, so turns_left should be 1
        self.assertEqual(self.game.level_state.turns_left, 1, "Should start with 1 turn left")
        
        # Simulate the banking flow:
        # 1. Set state to BANKED (as if we just banked)
        self.game.state_manager.set_state(self.game.state_manager.state.BANKED)
        
        # 2. Manually trigger TURN_END with reason=banked 
        # This will call reset_turn() which consumes the turn (turns_left becomes 0)
        # Then checks if turns_left == 0 and triggers failure
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason": "banked"}))
        
        # Check that LEVEL_FAILED event was published
        failed_events = [e for e in self.events if e.type == GameEventType.LEVEL_FAILED]
        self.assertGreater(len(failed_events), 0, f"Expected LEVEL_FAILED event to be published. Events: {[e.type for e in self.events]}")
        
        # Verify the event contains correct information
        failed_event = failed_events[0]
        self.assertEqual(failed_event.get("level_name"), "Test Level")
        self.assertEqual(failed_event.get("level_index"), 1)
        
        # Check that level_state.failed is set
        self.assertTrue(self.game.level_state.failed)
        
        # Check that game state is GAME_OVER
        self.assertEqual(self.game.state_manager.get_state(), self.game.state_manager.state.GAME_OVER)

if __name__ == '__main__':
    unittest.main()
