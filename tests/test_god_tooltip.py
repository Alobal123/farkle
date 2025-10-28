"""Test god tooltip shows name, lore, and level progression with highlighting."""
import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.ui.tooltip import resolve_hover


class GodTooltipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=42)
        # Draw once to initialize god rects
        self.game.draw()

    def test_demeter_tooltip_level_0(self):
        """Test Demeter tooltip at level 0 shows all levels unmarked."""
        demeter = self.game.gods.worshipped[0]
        self.assertEqual(demeter.name, "Demeter")
        self.assertEqual(demeter.level, 0)
        
        # Get Demeter's rect
        god_rect = getattr(demeter, '_rect', None)
        self.assertIsNotNone(god_rect, "Demeter should have a rect after draw")
        
        # Hover over Demeter
        tooltip = resolve_hover(self.game, (god_rect.x + 5, god_rect.y + 5))
        
        self.assertIsNotNone(tooltip)
        self.assertEqual(tooltip['title'], "Demeter")
        
        lines = tooltip['lines']
        # Should have lore
        self.assertIn("harvest", lines[0].lower())
        
        # Should have 3 level descriptions with [ ] markers (not achieved)
        level_lines = [l for l in lines if l.startswith('[ ]') or l.startswith('[X]')]
        self.assertEqual(len(level_lines), 3, "Should have 3 level progression lines")
        
        # All should be unmarked at level 0
        for line in level_lines:
            self.assertTrue(line.startswith('[ ]'), f"Line should be unmarked: {line}")

    def test_demeter_tooltip_level_1(self):
        """Test Demeter tooltip at level 1 shows first level highlighted."""
        from farkle.core.game_event import GameEvent, GameEventType
        from farkle.goals.goal import Goal
        
        demeter = self.game.gods.worshipped[0]
        
        # Find a nature goal
        nature_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
                break
        
        self.assertIsNotNone(nature_goal)
        
        # Complete 2 nature goals to reach level 1
        for i in range(2):
            self.game.event_listener.publish(
                GameEvent(
                    GameEventType.GOAL_FULFILLED,
                    payload={"goal": nature_goal}
                )
            )
        
        self.assertEqual(demeter.level, 1)
        
        # Redraw to update rects
        self.game.draw()
        god_rect = getattr(demeter, '_rect', None)
        
        # Hover over Demeter
        tooltip = resolve_hover(self.game, (god_rect.x + 5, god_rect.y + 5))
        
        self.assertIsNotNone(tooltip)
        lines = tooltip['lines']
        
        # Check level progression markers
        level_lines = [l for l in lines if l.startswith('[ ]') or l.startswith('[X]')]
        self.assertEqual(len(level_lines), 3)
        
        # Level 1 should be checked, others not
        self.assertTrue(level_lines[0].startswith('[X]'), "Level 1 should be achieved")
        self.assertTrue(level_lines[1].startswith('[ ]'), "Level 2 should not be achieved")
        self.assertTrue(level_lines[2].startswith('[ ]'), "Level 3 should not be achieved")
        
        # Should mention +20% bonus
        self.assertTrue(any('+20%' in line for line in lines))

    def test_ares_tooltip_shows_warfare_category(self):
        """Test Ares tooltip shows warfare-specific information."""
        # Find Ares
        ares = None
        for god in self.game.gods.worshipped:
            if god.name == "Ares":
                ares = god
                break
        
        self.assertIsNotNone(ares, "Ares should be in worshipped gods")
        
        god_rect = getattr(ares, '_rect', None)
        self.assertIsNotNone(god_rect)
        
        tooltip = resolve_hover(self.game, (god_rect.x + 5, god_rect.y + 5))
        
        self.assertIsNotNone(tooltip)
        self.assertEqual(tooltip['title'], "Ares")
        
        lines = tooltip['lines']
        # Should mention warfare
        self.assertTrue(any('warfare' in line.lower() for line in lines))
        
        # Should have war/battle in lore
        self.assertTrue(any('war' in line.lower() or 'battle' in line.lower() for line in lines))

    def test_hades_tooltip_shows_spirit_category(self):
        """Test Hades tooltip shows spirit-specific information."""
        # Find Hades
        hades = None
        for god in self.game.gods.worshipped:
            if god.name == "Hades":
                hades = god
                break
        
        self.assertIsNotNone(hades, "Hades should be in worshipped gods")
        
        god_rect = getattr(hades, '_rect', None)
        self.assertIsNotNone(god_rect)
        
        tooltip = resolve_hover(self.game, (god_rect.x + 5, god_rect.y + 5))
        
        self.assertIsNotNone(tooltip)
        self.assertEqual(tooltip['title'], "Hades")
        
        lines = tooltip['lines']
        # Should mention spirit
        self.assertTrue(any('spirit' in line.lower() for line in lines))
        
        # Should have underworld in lore
        self.assertTrue(any('underworld' in line.lower() for line in lines))

    def test_hermes_tooltip_shows_commerce_category(self):
        """Test Hermes tooltip shows commerce-specific information."""
        # Hermes is not in default worshipped gods, so manually add it
        from farkle.gods.hermes import Hermes
        
        # Replace one god with Hermes for testing
        hermes = Hermes(self.game)
        self.game.gods.worshipped[2] = hermes
        hermes.activate(self.game)
        
        # Redraw to get rect
        self.game.draw()
        
        god_rect = getattr(hermes, '_rect', None)
        self.assertIsNotNone(god_rect)
        
        tooltip = resolve_hover(self.game, (god_rect.x + 5, god_rect.y + 5))
        
        self.assertIsNotNone(tooltip)
        self.assertEqual(tooltip['title'], "Hermes")
        
        lines = tooltip['lines']
        # Should mention commerce
        self.assertTrue(any('commerce' in line.lower() for line in lines))
        
        # Should have trade in lore
        self.assertTrue(any('trade' in line.lower() for line in lines))

    def test_level_3_tooltip_shows_all_achieved(self):
        """Test god tooltip at level 3 shows all levels as achieved."""
        from farkle.core.game_event import GameEvent, GameEventType
        
        demeter = self.game.gods.worshipped[0]
        
        # Find a nature goal
        nature_goal = None
        for goal in self.game.level_state.goals:
            if goal.category == 'nature':
                nature_goal = goal
                break
        
        # Complete 12 nature goals to reach level 3
        for i in range(12):
            self.game.event_listener.publish(
                GameEvent(
                    GameEventType.GOAL_FULFILLED,
                    payload={"goal": nature_goal}
                )
            )
        
        self.assertEqual(demeter.level, 3)
        
        # Redraw
        self.game.draw()
        god_rect = getattr(demeter, '_rect', None)
        
        tooltip = resolve_hover(self.game, (god_rect.x + 5, god_rect.y + 5))
        
        self.assertIsNotNone(tooltip)
        lines = tooltip['lines']
        
        # All levels should be checked
        level_lines = [l for l in lines if l.startswith('[ ]') or l.startswith('[X]')]
        self.assertEqual(len(level_lines), 3)
        
        for line in level_lines:
            self.assertTrue(line.startswith('[X]'), f"All levels should be achieved: {line}")
        
        # Should mention double rewards for level 3
        self.assertTrue(any('Double' in line for line in lines))


if __name__ == '__main__':
    unittest.main()
