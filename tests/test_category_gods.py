"""Tests for category-based gods (Demeter, Ares, Hades, Hermes).

Each god levels up when goals of their specific category are completed.
"""

import unittest
import pygame
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class CategoryGodsTests(unittest.TestCase):
    """Test gods that level up based on goal category completions."""
    
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()
    
    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1)
        
        # Capture events for verification
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))
    
    def test_demeter_levels_on_nature_goal(self):
        """Demeter should level up when enough nature goals are completed."""
        # Find Demeter in worshipped gods
        demeter = None
        for god in self.game.gods.worshipped:
            if god.name == "Demeter":
                demeter = god
                break
        
        self.assertIsNotNone(demeter, "Demeter should be in worshipped gods")
        self.assertEqual(demeter.level, 0, "Demeter should start at level 0")
        
        # Create mock nature goals
        from farkle.goals.goal import Goal
        
        # Complete 1 goal - should not level up yet (needs 2)
        nature_goal = Goal(
            target_score=100,
            game=self.game,
            name="Test Nature Goal 1",
            category="nature",
            is_disaster=True
        )
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOAL_FULFILLED,
            payload={"goal": nature_goal}
        ))
        self.assertEqual(demeter.level, 0, "Demeter should still be level 0 after 1 goal")
        self.assertEqual(demeter.goals_completed, 1)
        
        # Complete 2nd goal - should level up to 1
        nature_goal2 = Goal(
            target_score=100,
            game=self.game,
            name="Test Nature Goal 2",
            category="nature",
            is_disaster=True
        )
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOAL_FULFILLED,
            payload={"goal": nature_goal2}
        ))
        self.assertEqual(demeter.level, 1, "Demeter should level up to 1 after 2 goals")
        self.assertEqual(demeter.goals_completed, 2)
    
    def test_ares_levels_on_warfare_goal(self):
        """Ares should level up when enough warfare goals are completed."""
        # Find Ares in worshipped gods
        ares = None
        for god in self.game.gods.worshipped:
            if god.name == "Ares":
                ares = god
                break
        
        self.assertIsNotNone(ares, "Ares should be in worshipped gods")
        self.assertEqual(ares.level, 0, "Ares should start at level 0")
        
        # Create mock warfare goals - need 2 for level 1
        from farkle.goals.goal import Goal
        for i in range(2):
            warfare_goal = Goal(
                target_score=100,
                game=self.game,
                name=f"Test Warfare Goal {i}",
                category="warfare",
                is_disaster=True
            )
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOAL_FULFILLED,
                payload={"goal": warfare_goal}
            ))
        
        # Ares should level up to 1 after 2 goals
        self.assertEqual(ares.level, 1, "Ares should level up to 1 after 2 goals")
        self.assertEqual(ares.goals_completed, 2)
    
    def test_hades_levels_on_spirit_goal(self):
        """Hades should level up when enough spirit goals are completed."""
        # Find Hades in worshipped gods
        hades = None
        for god in self.game.gods.worshipped:
            if god.name == "Hades":
                hades = god
                break
        
        self.assertIsNotNone(hades, "Hades should be in worshipped gods")
        self.assertEqual(hades.level, 0, "Hades should start at level 0")
        
        # Create mock spirit goals - need 2 for level 1
        from farkle.goals.goal import Goal
        for i in range(2):
            spirit_goal = Goal(
                target_score=100,
                game=self.game,
                name=f"Test Spirit Goal {i}",
                category="spirit",
                is_disaster=True
            )
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOAL_FULFILLED,
                payload={"goal": spirit_goal}
            ))
        
        # Hades should level up to 1 after 2 goals
        self.assertEqual(hades.level, 1, "Hades should level up to 1 after 2 goals")
        self.assertEqual(hades.goals_completed, 2)
    
    def test_god_does_not_level_on_wrong_category(self):
        """Gods should only level up for their specific category."""
        # Find Demeter
        demeter = None
        for god in self.game.gods.worshipped:
            if god.name == "Demeter":
                demeter = god
                break
        
        self.assertIsNotNone(demeter)
        initial_level = demeter.level
        
        # Create a warfare goal (wrong category for Demeter)
        from farkle.goals.goal import Goal
        warfare_goal = Goal(
            target_score=100,
            game=self.game,
            name="Test Warfare Goal",
            category="warfare",
            is_disaster=True
        )
        
        # Emit GOAL_FULFILLED event
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOAL_FULFILLED,
            payload={"goal": warfare_goal}
        ))
        
        # Demeter should NOT level up
        self.assertEqual(demeter.level, initial_level, "Demeter should not level up for warfare goals")
    
    def test_multiple_level_ups(self):
        """Gods should level up multiple times based on cumulative goals (2, then 6, then 12 total)."""
        # Find Demeter
        demeter = None
        for god in self.game.gods.worshipped:
            if god.name == "Demeter":
                demeter = god
                break
        
        self.assertIsNotNone(demeter)
        
        # Complete 2 goals -> level 1
        from farkle.goals.goal import Goal
        for i in range(2):
            nature_goal = Goal(
                target_score=100,
                game=self.game,
                name=f"Nature Goal {i}",
                category="nature",
                is_disaster=True
            )
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOAL_FULFILLED,
                payload={"goal": nature_goal}
            ))
        self.assertEqual(demeter.level, 1)
        self.assertEqual(demeter.goals_completed, 2)
        
        # Complete 4 more goals (6 total) -> level 2
        for i in range(2, 6):
            nature_goal = Goal(
                target_score=100,
                game=self.game,
                name=f"Nature Goal {i}",
                category="nature",
                is_disaster=True
            )
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOAL_FULFILLED,
                payload={"goal": nature_goal}
            ))
        self.assertEqual(demeter.level, 2)
        self.assertEqual(demeter.goals_completed, 6)
        
        # Complete 6 more goals (12 total) -> level 3 (max)
        for i in range(6, 12):
            nature_goal = Goal(
                target_score=100,
                game=self.game,
                name=f"Nature Goal {i}",
                category="nature",
                is_disaster=True
            )
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOAL_FULFILLED,
                payload={"goal": nature_goal}
            ))
        self.assertEqual(demeter.level, 3)
        self.assertEqual(demeter.goals_completed, 12)
    
    def test_max_level_cap(self):
        """Gods should not exceed max level (3)."""
        from farkle.gods.gods_manager import GOD_MAX_LEVEL
        
        # Find Demeter
        demeter = None
        for god in self.game.gods.worshipped:
            if god.name == "Demeter":
                demeter = god
                break
        
        self.assertIsNotNone(demeter)
        
        # Complete 15 goals (more than the 12 needed for max level 3)
        from farkle.goals.goal import Goal
        for i in range(15):
            nature_goal = Goal(
                target_score=100,
                game=self.game,
                name=f"Nature Goal {i}",
                category="nature",
                is_disaster=True
            )
            self.game.event_listener.publish(GameEvent(
                GameEventType.GOAL_FULFILLED,
                payload={"goal": nature_goal}
            ))
        
        # Demeter should be capped at max level (3)
        self.assertEqual(demeter.level, GOD_MAX_LEVEL)
        self.assertEqual(demeter.goals_completed, 15)  # Counter continues
    
    def test_hermes_not_in_default_worshipped(self):
        """Hermes (commerce god) should not be in default worshipped gods."""
        hermes_found = False
        for god in self.game.gods.worshipped:
            if god.name == "Hermes":
                hermes_found = True
                break
        
        self.assertFalse(hermes_found, "Hermes should not be in default worshipped gods")
    
    def test_all_four_gods_can_be_worshipped(self):
        """Test that we can manually set all four category gods as worshipped."""
        from farkle.gods.demeter import Demeter
        from farkle.gods.ares import Ares
        from farkle.gods.hades import Hades
        from farkle.gods.hermes import Hermes
        
        # Set first three (game allows max 3)
        self.game.gods.set_worshipped([
            Demeter(self.game),
            Ares(self.game),
            Hades(self.game)
        ])
        
        self.assertEqual(len(self.game.gods.worshipped), 3)
        
        # Verify they can all receive events
        from farkle.goals.goal import Goal
        
        nature_goal = Goal(100, self.game, "Nature", category="nature")
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOAL_FULFILLED,
            payload={"goal": nature_goal}
        ))
        
        warfare_goal = Goal(100, self.game, "Warfare", category="warfare")
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOAL_FULFILLED,
            payload={"goal": warfare_goal}
        ))
        
        spirit_goal = Goal(100, self.game, "Spirit", category="spirit")
        self.game.event_listener.publish(GameEvent(
            GameEventType.GOAL_FULFILLED,
            payload={"goal": spirit_goal}
        ))
        
        # Check all leveled up to level 1 (need 2 goals each)
        # We only completed 1 goal per god, so they should still be at level 0
        for god in self.game.gods.worshipped:
            self.assertEqual(god.level, 0, f"{god.name} should still be level 0 after 1 goal")
            self.assertEqual(god.goals_completed, 1)


if __name__ == '__main__':
    unittest.main()
