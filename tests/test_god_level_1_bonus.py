"""Test that level 1 gods give +20% to their category goals."""

import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType


class GodLevel1BonusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1)
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))

    def test_demeter_level_1_gives_20_percent_bonus_to_nature_goals(self):
        """Demeter at level 1 should give +20% to nature goals."""
        demeter = self.game.gods.worshipped[0]
        self.assertEqual(demeter.name, "Demeter")
        
        # Find nature and non-nature goals
        nature_goal = None
        other_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
            elif goal.category != 'nature' and not other_goal:
                other_goal = goal
        
        self.assertIsNotNone(nature_goal, "Should have a nature goal")
        self.assertIsNotNone(other_goal, "Should have a non-nature goal")
        
        # Level up Demeter to level 1 (requires 2 nature goals)
        for i in range(2):
            self.game.event_listener.publish(
                GameEvent(
                    GameEventType.GOAL_FULFILLED,
                    payload={
                        "goal_name": nature_goal.name,
                        "goal": nature_goal,
                        "reward_gold": 100
                    }
                )
            )
        
        self.assertEqual(demeter.level, 1)
        
        # Create score parts to preview (simulate locking dice worth 150 points)
        parts = [("SingleValue:1", 100), ("SingleValue:5", 50)]
        
        # Preview the score for nature goal (should be 180 = 150 * 1.2)
        preview_nature = self.game.scoring_manager.preview(parts, goal=nature_goal)
        
        # Preview the score for other goal (should be 150, no bonus)
        preview_other = self.game.scoring_manager.preview(parts, goal=other_goal)
        
        # Nature goal should get +20% bonus
        self.assertEqual(preview_nature['adjusted_total'], 180)
        
        # Other goal should not get bonus
        self.assertEqual(preview_other['adjusted_total'], 150)

    def test_ares_level_1_gives_20_percent_bonus_to_warfare_goals(self):
        """Ares at level 1 should give +20% to warfare goals."""
        # Find Ares in worshipped gods
        ares = None
        for god in self.game.gods.worshipped:
            if god.name == "Ares":
                ares = god
                break
        
        if not ares:
            self.skipTest("Ares not in worshipped gods for this seed")
        
        # Find warfare goal
        warfare_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'warfare':
                warfare_goal = goal
                break
        
        if not warfare_goal:
            self.skipTest("No warfare goal for this seed")
        
        # Level up Ares to level 1 (requires 2 warfare goals)
        for i in range(2):
            self.game.event_listener.publish(
                GameEvent(
                    GameEventType.GOAL_FULFILLED,
                    payload={
                        "goal_name": warfare_goal.name,
                        "goal": warfare_goal,
                        "reward_gold": 100
                    }
                )
            )
        
        self.assertEqual(ares.level, 1)
        
        # Create score parts to preview (simulate locking dice worth 150 points)
        parts = [("SingleValue:1", 100), ("SingleValue:5", 50)]
        
        preview = self.game.scoring_manager.preview(parts, goal=warfare_goal)
        
        # Should be 180 = 150 * 1.2
        self.assertEqual(preview['adjusted_total'], 180)

    def test_modifier_added_event_emitted_on_level_1(self):
        """Should emit SCORE_MODIFIER_ADDED when reaching level 1."""
        demeter = self.game.gods.worshipped[0]
        
        # Find nature goal
        nature_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
                break
        
        # Level up to 1
        for i in range(2):
            self.game.event_listener.publish(
                GameEvent(
                    GameEventType.GOAL_FULFILLED,
                    payload={
                        "goal_name": nature_goal.name,
                        "goal": nature_goal,
                        "reward_gold": 100
                    }
                )
            )
        
        # Find SCORE_MODIFIER_ADDED event
        modifier_events = [e for e in self.events if e.type == GameEventType.SCORE_MODIFIER_ADDED]
        
        # Should have at least one modifier added event
        self.assertGreater(len(modifier_events), 0)
        
        # Find the one from Demeter
        demeter_mod = None
        for e in modifier_events:
            if e.get('god') == 'Demeter':
                demeter_mod = e
                break
        
        self.assertIsNotNone(demeter_mod)
        self.assertEqual(demeter_mod.get('level'), 1)
        self.assertEqual(demeter_mod.get('description'), '+20% to nature goals')
        self.assertEqual(demeter_mod.get('data', {}).get('category'), 'nature')
        self.assertEqual(demeter_mod.get('data', {}).get('mult'), 1.2)


if __name__ == '__main__':
    unittest.main()
