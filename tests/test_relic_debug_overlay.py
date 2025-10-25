import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class RelicDebugOverlayTests(unittest.TestCase):
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
        
        # Force a draw call to build HUD & relic list (not strictly needed for debug lines method)
        self.game.renderer.draw()

    def test_debug_lines_include_relic(self):
        lines = self.game.relic_manager.active_relic_lines()
        # Expect at least one line containing Charm of Fives
        self.assertTrue(any('Charm of Fives' in ln for ln in lines), f"Expected Charm of Fives in relic debug lines: {lines}")

if __name__ == '__main__':
    unittest.main()
