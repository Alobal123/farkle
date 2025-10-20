import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_state_enum import GameState

class GodSwitchingGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock)
        # Force initial draw to layout gods
        self.game.renderer.draw()
        pygame.display.flip()
        # Ensure we have at least two gods to switch between
        gm = self.game.gods  # attribute is 'gods' in Game
        if len(gm.worshipped) < 2:
            from farkle.gods.gods_manager import God
            extra = God("TestGod")
            gm.worshipped.append(extra)
            # God draws rely on god.game for font access; assignment may trigger static analysis warning.
            try:
                extra.game = self.game  # type: ignore[attr-defined]
            except Exception:
                pass
            self.game.renderer.draw()
            pygame.display.flip()
        # After potential mutation, ensure gods manager draws to set _rect for each god
        try:
            gm.draw(self.game.screen)
        except Exception:
            pass

    def _find_second_god_rect(self):
        gm = self.game.gods
        if len(gm.worshipped) < 2:
            return None
        second = gm.worshipped[1]
        return getattr(second, '_rect', None)

    def test_switch_allowed_in_pre_roll(self):
        self.assertEqual(self.game.state_manager.get_state(), GameState.PRE_ROLL)
        r = self._find_second_god_rect()
        self.assertIsNotNone(r, 'Second god rect should be available')
        if r is None:
            return
        # Simulate click
        consumed = self.game.gods.handle_click(self.game, (r.centerx, r.centery))
        self.assertTrue(consumed, 'Click should be consumed when switching in PRE_ROLL')
        self.assertEqual(self.game.gods.active_index, 1, 'Active god should switch to second index')

    def test_switch_blocked_during_rolling(self):
        # Transition to rolling (simulate a roll start)
        self.game.state_manager.transition_to_rolling()
        self.assertEqual(self.game.state_manager.get_state(), GameState.ROLLING)
        prev_active = self.game.gods.active_index
        r = self._find_second_god_rect()
        self.assertIsNotNone(r, 'Second god rect should be available')
        if r is None:
            return
        consumed = self.game.gods.handle_click(self.game, (r.centerx, r.centery))
        # Should either be ignored (False) or consumed for message (True) but NOT change active_index
        self.assertEqual(self.game.gods.active_index, prev_active, 'Active god should not change after rolling started')

    def test_switch_allowed_in_banked(self):
        # Reach BANKED state: transition to rolling then simulate banking (state_manager handles transition via action)
        self.game.state_manager.transition_to_rolling()
        # Force banked state directly for test; real flow would lock + bank
        self.game.state_manager.transition_to_banked()
        self.assertEqual(self.game.state_manager.get_state(), GameState.BANKED)
        prev_active = self.game.gods.active_index
        # Ensure second god rect exists
        r = self._find_second_god_rect()
        self.assertIsNotNone(r, 'Second god rect should be available in BANKED')
        if r is None:
            return
        consumed = self.game.gods.handle_click(self.game, (r.centerx, r.centery))
        self.assertTrue(consumed, 'Click should be consumed when switching in BANKED')
        # Active index should change if second different
        if prev_active != 1:
            self.assertEqual(self.game.gods.active_index, 1, 'Active god should switch in BANKED state')

if __name__ == '__main__':
    unittest.main()
