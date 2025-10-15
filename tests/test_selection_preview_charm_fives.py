import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

class SelectionPreviewCharmFivesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def _prepare_game_with_charm(self):
        g = Game(self.screen, self.font, self.clock)
        g.player.gold = 500
        g.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index":1}))
        g.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC))
        return g

    def _force_single_five_selection(self, g):
        for i,d in enumerate(g.dice):
            d.value = 5 if i==0 else 2
            d.held = False
            d.selected = False
        g.mark_scoring_dice(); g.dice[0].selected = True

    def test_level1_selection_preview(self):
        g = self._prepare_game_with_charm()
        self._force_single_five_selection(g)
        raw_sel, selective_sel, final_sel, total_mult = g.selection_preview()
        self.assertEqual(raw_sel, 50)
        self.assertEqual(selective_sel, 100, f"Expected selective 100, got {selective_sel}")
        self.assertEqual(final_sel, 100)

    def test_level2_selection_preview_persists(self):
        g = self._prepare_game_with_charm()
        # Fast-forward to level 2
        for goal in g.level_state.goals:
            goal.remaining = 0
        g.level_state.completed = True
        g.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason":"level_complete"}))
        # Now on level 2 with relic intact
        self._force_single_five_selection(g)
        raw_sel, selective_sel, final_sel, total_mult = g.selection_preview()
        self.assertEqual(raw_sel, 50)
        self.assertEqual(selective_sel, 100)
        # No global multipliers anymore: final equals selective and multiplier is 1.0
        self.assertEqual(final_sel, selective_sel)
        self.assertEqual(total_mult, 1.0)

if __name__ == '__main__':
    unittest.main()
