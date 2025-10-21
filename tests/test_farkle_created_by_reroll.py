import unittest, pygame, random
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class FarkleCreatedByRerollTests(unittest.TestCase):
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

    def test_reroll_can_create_farkle(self):
        # Roll once to enter ROLLING
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
        self.assertEqual(self.game.state_manager.get_state().name, 'ROLLING')
        # Force all dice scoring eligible THEN clear them via manipulated values to ensure reroll can produce farkle
        pattern = [2,3,4,6,2,3]
        for i, d in enumerate(self.game.dice):
            d.value = pattern[i]
            d.selected = False
            d.scoring_eligible = False
            d.held = False
        self.game.mark_scoring_dice(); self.assertTrue(self.game.check_farkle())
        # Rescue by setting one scoring die (1) so current state is not farkle
        self.game.dice[0].value = 1
        self.game.mark_scoring_dice(); self.assertFalse(self.game.check_farkle())
        # Activate reroll ability
        reroll = self.game.ability_manager.get('reroll')
        self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
        reroll = self.game.ability_manager.get('reroll')
        self.assertTrue(reroll and reroll.selecting)
        # Monkeypatch randint to always yield non-scoring (2) replacing the lone scoring die -> produces farkle
        original_randint = random.randint
        random.randint = lambda a,b: 2
        try:
            self.assertTrue(self.game.ability_manager.attempt_target('die', 0))
        finally:
            random.randint = original_randint
        self.assertEqual(self.game.state_manager.get_state().name, 'FARKLE', 'Reroll should have created a new farkle state')
        self.assertIn('farkle', self.game.message.lower())

if __name__ == '__main__':
    unittest.main()
