import unittest
import pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.temporary_effect import TemporaryEffect
from farkle.core.effect_type import EffectType
from farkle.core.game_event import GameEvent, GameEventType


class TestBlessing(TemporaryEffect):
    """Simple test blessing that tracks activation/deactivation."""
    def __init__(self, duration: int):
        super().__init__(name="Test Blessing", effect_type=EffectType.BLESSING, duration=duration)
        self.activated = False
        self.deactivated = False
    
    def on_activate(self, game):
        super().on_activate(game)
        self.activated = True
    
    def on_deactivate(self, game):
        super().on_deactivate(game)
        self.deactivated = True


class TestCurse(TemporaryEffect):
    """Simple test curse that tracks activation/deactivation."""
    def __init__(self, duration: int):
        super().__init__(name="Test Curse", effect_type=EffectType.CURSE, duration=duration)
        self.activated = False
        self.deactivated = False
    
    def on_activate(self, game):
        super().on_activate(game)
        self.activated = True
    
    def on_deactivate(self, game):
        super().on_deactivate(game)
        self.deactivated = True


class TemporaryEffectTests(unittest.TestCase):
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

    def test_blessing_applied_and_tracked(self):
        """Test that a blessing can be applied to player and tracked."""
        blessing = TestBlessing(duration=3)
        self.game.player.apply_effect(blessing)
        
        self.assertIn(blessing, self.game.player.active_effects)
        self.assertTrue(blessing.active)
        self.assertEqual(blessing.duration, 3)
        self.assertEqual(blessing.effect_type, EffectType.BLESSING)

    def test_curse_applied_and_tracked(self):
        """Test that a curse can be applied to player and tracked."""
        curse = TestCurse(duration=2)
        self.game.player.apply_effect(curse)
        
        self.assertIn(curse, self.game.player.active_effects)
        self.assertTrue(curse.active)
        self.assertEqual(curse.duration, 2)
        self.assertEqual(curse.effect_type, EffectType.CURSE)

    def test_effect_duration_decreases_on_turn_end_banked(self):
        """Duration decrements once when a banked turn ends."""
        blessing = TestBlessing(duration=3)
        self.game.player.apply_effect(blessing)
        # Simulate end of turn (banked)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={'reason': 'banked'}))
        self.assertEqual(blessing.duration, 2)
        self.assertIn(blessing, self.game.player.active_effects)

    def test_effect_duration_decreases_on_farkle_turn_end(self):
        """Decrements on TURN_END(farkle)."""
        curse = TestCurse(duration=2)
        self.game.player.apply_effect(curse)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={'reason': 'farkle'}))
        self.assertEqual(curse.duration, 1)
        self.assertIn(curse, self.game.player.active_effects)

    def test_effect_auto_deactivates_at_zero_duration_on_turn_end(self):
        """Effect at duration 1 expires after a single qualifying TURN_END."""
        blessing = TestBlessing(duration=1)
        self.game.player.apply_effect(blessing)
        self.assertIn(blessing, self.game.player.active_effects)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={'reason': 'banked'}))
        self.assertEqual(blessing.duration, 0)
        self.assertTrue(blessing.deactivated)
        self.assertNotIn(blessing, self.game.player.active_effects)

    def test_multiple_effects_decrement_once_per_turn_end(self):
        """Effects decrement once per completed turn; TURN_START resets guard."""
        blessing = TestBlessing(duration=3)
        curse = TestCurse(duration=2)
        self.game.player.apply_effect(blessing)
        self.game.player.apply_effect(curse)
        # First completed turn (banked)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={'reason': 'banked'}))
        self.assertEqual((blessing.duration, curse.duration), (2,1))
        # New turn start resets guard
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={'turns_left': 5}))
        # Second completed turn (farkle)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={'reason': 'farkle'}))
        self.assertEqual((blessing.duration, curse.duration), (1,0))
        self.assertTrue(curse.deactivated)
        self.assertIn(blessing, self.game.player.active_effects)

    def test_goal_fulfilled_no_longer_decrements(self):
        """GOAL_FULFILLED should not decrement under new semantics."""
        blessing = TestBlessing(duration=2)
        self.game.player.apply_effect(blessing)
        self.game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={'goal_name': 'TestGoal'}))
        self.assertEqual(blessing.duration, 2)
        # Ending turn now decrements
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={'reason': 'banked'}))
        self.assertEqual(blessing.duration, 1)

    def test_manual_effect_removal(self):
        """Test that effects can be manually removed."""
        blessing = TestBlessing(duration=5)
        self.game.player.apply_effect(blessing)
        
        self.assertIn(blessing, self.game.player.active_effects)
        
        self.game.player.remove_effect(blessing)
        
        self.assertNotIn(blessing, self.game.player.active_effects)
        self.assertTrue(blessing.deactivated)

    def test_level_complete_turn_end_decrements(self):
        """TURN_END(level_complete) now decrements (included in whitelist)."""
        blessing = TestBlessing(duration=2)
        self.game.player.apply_effect(blessing)
        self.game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={'reason': 'level_complete'}))
        self.assertEqual(blessing.duration, 1)

    # Starter effect removed from initialization; presence test deleted.


if __name__ == '__main__':
    unittest.main()
