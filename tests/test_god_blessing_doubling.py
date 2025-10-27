"""Test that god level 3 doubles blessing duration (2 turns instead of 1)."""
import unittest
import pygame
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class GodBlessingDoublingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=42)

    def test_level_3_god_doubles_blessing(self):
        """Test that level 3 god grants blessing twice (2 turn duration)."""
        from farkle.gods.demeter import Demeter
        from farkle.goals.goal import Goal
        
        # Set up Demeter at level 3
        demeter = Demeter(self.game)
        demeter.level = 3
        demeter.activate(self.game)
        
        # Create a nature goal with blessing reward
        goal = Goal(100, self.game, "Test Nature Goal", category="nature", 
                   reward_blessing="double_score", is_disaster=True)
        goal.remaining = 0
        
        # Claim reward - should apply blessing twice
        goal.claim_reward()
        
        # Check player has 2 blessings active (same type applied twice)
        self.assertEqual(len(self.game.player.active_effects), 2, 
                        "Should have 2 blessings (doubled)")
        
        # Both should be DoubleScoreBlessing
        from farkle.blessings import DoubleScoreBlessing
        for effect in self.game.player.active_effects:
            self.assertIsInstance(effect, DoubleScoreBlessing)
    
    def test_non_matching_category_no_double_blessing(self):
        """Test that gods don't double blessings from non-matching categories."""
        from farkle.gods.demeter import Demeter
        from farkle.goals.goal import Goal
        
        # Set up Demeter at level 3
        demeter = Demeter(self.game)
        demeter.level = 3
        demeter.activate(self.game)
        
        # Create a warfare goal (not nature)
        goal = Goal(100, self.game, "Test Warfare Goal", category="warfare", 
                   reward_blessing="double_score", is_disaster=True)
        goal.remaining = 0
        
        # Claim reward
        goal.claim_reward()
        
        # Should have only 1 blessing (not doubled)
        self.assertEqual(len(self.game.player.active_effects), 1, 
                        "Should have only 1 blessing (no god bonus)")
    
    def test_level_2_god_no_double_blessing(self):
        """Test that level 2 gods don't double blessings."""
        from farkle.gods.ares import Ares
        from farkle.goals.goal import Goal
        
        # Set up Ares at level 2 (not level 3)
        ares = Ares(self.game)
        ares.level = 2
        ares.activate(self.game)
        
        # Create a warfare goal with blessing
        goal = Goal(100, self.game, "Test Warfare Goal", category="warfare", 
                   reward_blessing="double_score", is_disaster=True)
        goal.remaining = 0
        
        # Claim reward
        goal.claim_reward()
        
        # Should have only 1 blessing (no god bonus at level 2)
        self.assertEqual(len(self.game.player.active_effects), 1, 
                        "Should have only 1 blessing at level 2")
    
    def test_blessing_duration_effectively_doubled(self):
        """Test that two blessings mean 2 turns of effect."""
        from farkle.gods.hades import Hades
        from farkle.goals.goal import Goal
        from farkle.blessings import DoubleScoreBlessing
        
        # Set up Hades at level 3
        hades = Hades(self.game)
        hades.level = 3
        hades.activate(self.game)
        
        # Create a spirit goal with blessing
        goal = Goal(100, self.game, "Test Spirit Goal", category="spirit", 
                   reward_blessing="double_score", is_disaster=True)
        goal.remaining = 0
        
        # Claim reward
        goal.claim_reward()
        
        # Should have 2 blessings
        self.assertEqual(len(self.game.player.active_effects), 2)
        
        # Both should have duration=1 initially
        for effect in self.game.player.active_effects:
            self.assertEqual(effect.duration, 1)
        
        # Simulate turn start (decrements duration)
        # Blessings granted mid-turn skip the first TURN_START, so we need 2 calls
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={}))
        
        # Both blessings should still be active (first TURN_START is skipped)
        active_blessings = [e for e in self.game.player.active_effects 
                           if isinstance(e, DoubleScoreBlessing)]
        self.assertEqual(len(active_blessings), 2, 
                        "Both blessings should remain (first TURN_START skipped)")
        
        # Simulate second turn start (should decrement both)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={}))
        
        # Both blessings should expire now (duration 1 - 1 = 0)
        active_blessings = [e for e in self.game.player.active_effects 
                           if isinstance(e, DoubleScoreBlessing)]
        self.assertEqual(len(active_blessings), 0, 
                        "All blessings should expire after second TURN_START")
    
    def test_blessing_events_tracked(self):
        """Test that blessing events are properly emitted."""
        from farkle.gods.hermes import Hermes
        from farkle.goals.goal import Goal
        
        # Set up Hermes at level 3
        hermes = Hermes(self.game)
        hermes.level = 3
        hermes.activate(self.game)
        
        # Track events
        events = []
        self.game.event_listener.subscribe(lambda e: events.append(e))
        
        # Create a commerce goal with blessing
        goal = Goal(100, self.game, "Test Commerce Goal", category="commerce", 
                   reward_blessing="double_score", is_disaster=True)
        goal.remaining = 0
        
        # Claim reward
        goal.claim_reward()
        
        # Check events
        blessing_rewarded_events = [e for e in events if e.type == GameEventType.BLESSING_REWARDED]
        blessing_gained_events = [e for e in events if e.type == GameEventType.BLESSING_GAINED]
        
        # Should have 2 BLESSING_REWARDED (goal + god)
        self.assertEqual(len(blessing_rewarded_events), 2, 
                        "Should have 2 BLESSING_REWARDED events")
        
        # Should have 2 BLESSING_GAINED (goal + god)
        self.assertEqual(len(blessing_gained_events), 2, 
                        "Should have 2 BLESSING_GAINED events")
        
        # First REWARDED should be from goal
        self.assertEqual(blessing_rewarded_events[0].get("source"), "goal_reward")
        self.assertEqual(blessing_rewarded_events[0].get("goal_category"), "commerce")
        
        # Second REWARDED should be from god
        self.assertEqual(blessing_rewarded_events[1].get("source"), "god_bonus")
        self.assertEqual(blessing_rewarded_events[1].get("god_name"), "Hermes")


if __name__ == '__main__':
    unittest.main()
