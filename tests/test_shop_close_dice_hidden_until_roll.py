import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class TestShopCloseDiceHiddenUntilRoll(unittest.TestCase):
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
        # Trigger level advancement completion -> shop opens
        self.game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": self.game.level_index}))
        self.assertTrue(self.game.relic_manager.shop_open)
        # Close shop
        self.game.event_listener.publish(GameEvent(GameEventType.SHOP_CLOSED, payload={"skipped": True}))
        # After close, dice should be hidden
        # After shop close we are in PRE_ROLL; dice should not draw
        for d in self.game.dice:
            self.assertFalse(d.should_draw(self.game), 'Dice should not draw after shop close before first roll')

    def test_dice_not_clickable_when_hidden(self):
        # Attempt to click where a die would be; ensure no selection happens
        any_die = self.game.dice[0]
        from farkle.ui.settings import DICE_SIZE
        mx, my = any_die.x + DICE_SIZE//2, any_die.y + DICE_SIZE//2
        before_selected = any_die.selected
        consumed = self.game._handle_die_click(mx, my, button=1)
        self.assertFalse(consumed, 'Click should not be consumed when dice hidden')
        self.assertEqual(any_die.selected, before_selected, 'Die selection state should not change while hidden')

    def test_dice_visible_after_first_roll(self):
        # Perform roll
        self.game.handle_roll()
        for d in self.game.dice:
            self.assertTrue(d.should_draw(self.game), 'Dice should draw after first roll post shop')
        # Find a scoring-eligible die (selection only allowed on scoring dice)
        scoring_die = next((d for d in self.game.dice if not d.held and getattr(d, 'scoring_eligible', False)), None)
        self.assertIsNotNone(scoring_die, 'After first roll at least one die should be scoring eligible')
        if scoring_die is None:
            return  # safety for static analyzer; assertion already fails test
        from farkle.ui.settings import DICE_SIZE
        mx, my = scoring_die.x + DICE_SIZE//2, scoring_die.y + DICE_SIZE//2
        consumed = self.game._handle_die_click(mx, my, button=1)
        self.assertTrue(consumed, 'Click on a scoring die should be consumed after dice become visible')

if __name__ == '__main__':
    unittest.main()
