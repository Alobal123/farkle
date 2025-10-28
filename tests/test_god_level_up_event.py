"""Test that gods emit GOD_LEVEL_UP events when leveling up."""
import unittest
import pygame
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT


class GodLevelUpEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1)
        
        # Initialize default gods for testing (Demeter, Ares, Hades)
        from farkle.gods.demeter import Demeter
        from farkle.gods.ares import Ares
        from farkle.gods.hades import Hades
        self.game.gods.set_worshipped([Demeter(self.game), Ares(self.game), Hades(self.game)])
        
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))

    def test_demeter_emits_god_level_up_event(self):
        """Demeter should emit GOD_LEVEL_UP when leveling up from nature goal."""
        demeter = self.game.gods.worshipped[0]
        self.assertEqual(demeter.name, "Demeter")
        self.assertEqual(demeter.level, 0)
        
        # Find a nature goal
        nature_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
                break
        
        self.assertIsNotNone(nature_goal, "Should have at least one nature goal")
        
        # Trigger 2 goal completions (required for level 1)
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
        
        # Check level up
        self.assertEqual(demeter.level, 1)
        
        # Check GOD_LEVEL_UP event was emitted
        god_level_up_events = [e for e in self.events if e.type == GameEventType.GOD_LEVEL_UP]
        self.assertEqual(len(god_level_up_events), 1)
        
        event = god_level_up_events[0]
        self.assertEqual(event.get('god_name'), 'Demeter')
        self.assertEqual(event.get('old_level'), 0)
        self.assertEqual(event.get('new_level'), 1)
        self.assertEqual(event.get('category'), 'nature')
        self.assertEqual(event.get('progress'), 2)
        self.assertEqual(event.get('goals_needed'), 2)

    def test_no_event_when_at_max_level(self):
        """Gods should not emit GOD_LEVEL_UP when already at max level."""
        from farkle.gods.gods_manager import GOD_MAX_LEVEL
        
        demeter = self.game.gods.worshipped[0]
        demeter.level = GOD_MAX_LEVEL
        
        # Find a nature goal
        nature_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
                break
        
        # Trigger goal completion
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
        
        # Level should stay at max
        self.assertEqual(demeter.level, GOD_MAX_LEVEL)
        
        # Should not emit GOD_LEVEL_UP since already at max
        god_level_up_events = [e for e in self.events if e.type == GameEventType.GOD_LEVEL_UP]
        self.assertEqual(len(god_level_up_events), 0)


if __name__ == '__main__':
    unittest.main()
