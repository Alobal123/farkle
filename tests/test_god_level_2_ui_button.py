"""Test that UI buttons are created when gods level up to level 2."""
import unittest
import pygame
from farkle.game import Game
from farkle.level.level import Level
from farkle.goals.goal import Goal
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType


class GodLevel2UIButtonTests(unittest.TestCase):
    """Test god level 2 UI button creation."""
    
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()
    
    def setUp(self):
        # Create a custom level with many nature goals
        # Level goals are tuples: (name, target, is_disaster, reward_gold, reward_income, reward_blessing, flavor_text, category, persona, reward_faith)
        goals = tuple([
            (f"Nature Goal {i}", 100, True, 0, 0, "", "", "nature", "", 0) 
            for i in range(10)
        ])
        level = Level(name="Test Level", max_turns=50, goals=goals)
        
        # Create game with custom level
        self.game = Game(self.screen, self.font, self.clock, level=level, rng_seed=1)
        
        # Initialize default gods for testing (Demeter, Ares, Hades)
        from farkle.gods.demeter import Demeter
        from farkle.gods.ares import Ares
        from farkle.gods.hades import Hades
        self.game.gods.set_worshipped([Demeter(self.game), Ares(self.game), Hades(self.game)])
        
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))
    
    def test_sanctify_button_created_on_level_2(self):
        """When Demeter reaches level 2, a Sanctify button should be created."""
        # Check initial button count (should be 4: roll, bank, next, reroll)
        initial_button_count = len(self.game.ui_buttons)
        self.assertEqual(initial_button_count, 4)
        
        # Check that no sanctify button exists yet
        sanctify_buttons = [b for b in self.game.ui_buttons if 'sanctify' in b.name.lower()]
        self.assertEqual(len(sanctify_buttons), 0)
        
        # Complete 6 nature goals to reach level 2 (2 for level 1, 4 more for level 2)
        completed_count = 0
        while completed_count < 6:
            goal = None
            for g in self.game.level_state.goals:
                if g.category == 'nature' and not g.is_fulfilled():
                    goal = g
                    break
            
            if goal:
                # Simulate goal completion
                goal.pending_raw = goal.remaining
                goal.remaining = 0
                self.game.event_listener.publish(GameEvent(
                    GameEventType.GOAL_FULFILLED,
                    payload={'goal': goal}
                ))
                completed_count += 1
            else:
                # No more nature goals available, break
                break
        
        # Verify we completed enough goals
        demeter = self.game.gods.worshipped[0]
        # Should be level 2 if we completed 6 goals (2 for level 1, 4 more for level 2)
        self.assertEqual(completed_count, 6)
        self.assertEqual(demeter.level, 2)
        
        # NOW a sanctify button should exist
        sanctify_buttons = [b for b in self.game.ui_buttons if 'sanctify' in b.name.lower()]
        self.assertEqual(len(sanctify_buttons), 1)
        
        # Verify button is for nature sanctify
        sanctify_btn = sanctify_buttons[0]
        self.assertEqual(sanctify_btn.name, 'sanctify_nature')
    
    def test_multiple_god_buttons_created(self):
        """If multiple gods reach level 2, each should have its own button."""
        # This is more of a conceptual test - in real gameplay it's hard to 
        # get multiple gods to level 2 quickly, but we can verify the mechanism
        
        # For now, just verify that the button rebuild mechanism works
        initial_count = len(self.game.ui_buttons)
        
        # Manually trigger a rebuild
        self.game._rebuild_ui_buttons()
        
        # Should have same count if no new abilities
        self.assertEqual(len(self.game.ui_buttons), initial_count)


if __name__ == '__main__':
    unittest.main()
