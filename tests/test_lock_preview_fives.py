import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class LockPreviewFivesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = 0
        if hasattr(pygame, 'HIDDEN'): flags |= pygame.HIDDEN
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, skip_god_selection=True)
        
        # Directly create and activate the "Charm of Fives" relic
        from farkle.relics.relic import Relic
        from farkle.scoring.score_modifiers import FlatRuleBonus
        
        charm_of_fives = Relic(
            id="charm_of_fives",
            name="Charm of Fives",
            cost=30,
            description="Get a flat bonus of 50 points for scoring with single 5s.",
            modifiers=[FlatRuleBonus(rule_key="SingleValue:5", amount=50)]
        )
        
        # Add the relic to the manager and activate it
        self.game.relic_manager.active_relics.append(charm_of_fives)
        charm_of_fives.activate(self.game)

    def test_single_five_lock_shows_bonus_preview(self):
        # Force dice values: single five selectable
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i==0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        self.game.handle_lock()
        msg = self.game.message
        # Message should include raw->adjusted path '50 -> 100'
        self.assertIn('50 -> 100', msg, f"Expected preview '50 -> 100' in lock message, got: {msg}")

if __name__ == '__main__':
    unittest.main()
