"""Test that level 2 gods grant Sanctify ability to change goal categories."""

import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType


class GodLevel2SanctifyTests(unittest.TestCase):
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

    def test_demeter_level_2_grants_sanctify_ability(self):
        """Demeter at level 2 should grant Sanctify ability."""
        demeter = self.game.gods.worshipped[0]
        self.assertEqual(demeter.name, "Demeter")
        
        # Find nature goal
        nature_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
                break
        
        self.assertIsNotNone(nature_goal)
        
        # Level up Demeter to level 2 (requires 6 total nature goals: 2 for level 1, 4 more for level 2)
        for i in range(6):
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
        
        self.assertEqual(demeter.level, 2)
        
        # Check that sanctify ability was registered
        sanctify_ability = self.game.ability_manager.get('sanctify_nature')
        self.assertIsNotNone(sanctify_ability, "Sanctify ability should be registered")
        self.assertEqual(sanctify_ability.name, "Sanctify (Demeter)")
        self.assertEqual(sanctify_ability.god_category, "nature")
        self.assertEqual(sanctify_ability.charges_per_level, 1)
        self.assertEqual(sanctify_ability.available(), 1)

    def test_sanctify_changes_goal_category(self):
        """Sanctify ability should change a goal's category."""
        demeter = self.game.gods.worshipped[0]
        
        # Find nature and non-nature goals
        nature_goal = None
        other_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
            elif goal.category != 'nature' and not other_goal:
                other_goal = goal
        
        self.assertIsNotNone(nature_goal)
        self.assertIsNotNone(other_goal)
        
        old_category = other_goal.category
        self.assertNotEqual(old_category, 'nature')
        
        # Level up Demeter to level 2 (requires 6 total nature goals: 2 for level 1, 4 more for level 2)
        for i in range(6):
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
        
        sanctify_ability = self.game.ability_manager.get('sanctify_nature')
        self.assertIsNotNone(sanctify_ability)
        
        # Find goal index
        goals = self.game.level_state.goals
        goal_index = goals.index(other_goal)
        
        # Execute sanctify on the other goal
        success = sanctify_ability.execute(self.game.ability_manager, target=goal_index)
        
        self.assertTrue(success)
        self.assertEqual(other_goal.category, 'nature')
        self.assertEqual(sanctify_ability.available(), 0, "Should have consumed one charge")
        
        # Check event was emitted
        ability_events = [e for e in self.events if e.type == GameEventType.ABILITY_EXECUTED]
        sanctify_events = [e for e in ability_events if e.get('ability') == 'sanctify_nature']
        self.assertEqual(len(sanctify_events), 1)
        
        event = sanctify_events[0]
        self.assertEqual(event.get('old_category'), old_category)
        self.assertEqual(event.get('new_category'), 'nature')
        self.assertEqual(event.get('god'), 'Demeter')

    def test_sanctify_cannot_change_already_matching_category(self):
        """Sanctify should not work on goals already matching the target category."""
        demeter = self.game.gods.worshipped[0]
        
        # Find nature goal
        nature_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
                break
        
        self.assertIsNotNone(nature_goal)
        
        # Level up Demeter to level 2
        for i in range(6):
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
        
        sanctify_ability = self.game.ability_manager.get('sanctify_nature')
        goals = self.game.level_state.goals
        goal_index = goals.index(nature_goal)
        
        # Try to sanctify a goal that's already nature category
        success = sanctify_ability.execute(self.game.ability_manager, target=goal_index)
        
        self.assertFalse(success, "Should fail to sanctify goal with same category")
        self.assertEqual(sanctify_ability.available(), 1, "Should not consume charge")

    def test_all_four_gods_get_sanctify_abilities(self):
        """All four gods should get their own sanctify abilities at level 2."""
        # Level up all gods to level 2 (6 goals each)
        for god in self.game.gods.worshipped:
            category = {
                'Demeter': 'nature',
                'Ares': 'warfare',
                'Hades': 'spirit',
                'Hermes': 'commerce'
            }.get(god.name)
            
            if not category:
                continue
            
            # Find a goal of this category
            goal = None
            for g in self.game.level_state.goals:
                if g.category == category:
                    goal = g
                    break
            
            if not goal:
                continue
            
            # Level up to 2 (requires 6 total goals: 2 for level 1, 4 more for level 2)
            for i in range(6):
                self.game.event_listener.publish(
                    GameEvent(
                        GameEventType.GOAL_FULFILLED,
                        payload={
                            "goal_name": goal.name,
                            "goal": goal,
                            "reward_gold": 100
                        }
                    )
                )
            
            self.assertEqual(god.level, 2)
            
            # Check sanctify ability
            ability_id = f'sanctify_{category}'
            ability = self.game.ability_manager.get(ability_id)
            self.assertIsNotNone(ability, f"{god.name} should have {ability_id} ability")
            self.assertEqual(ability.god_category, category)
            self.assertEqual(ability.available(), 1)


if __name__ == '__main__':
    unittest.main()
