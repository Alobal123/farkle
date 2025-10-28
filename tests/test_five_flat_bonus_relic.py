import unittest, pygame
from farkle.game import Game
from farkle.ui.settings import WIDTH, HEIGHT
from farkle.core.game_event import GameEvent, GameEventType

class FiveFlatBonusRelicTests(unittest.TestCase):
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

    def test_single_five_flat_bonus(self):
        # Set dice: one 5 scoring single and others non-scoring
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i == 0 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        self.game.dice[0].selected = True
        # Lock and then bank
        self.game.handle_lock()
        captured = {}
        def cap(ev):
            if ev.type == GameEventType.SCORE_APPLIED:
                captured.update(ev.payload)
        self.game.event_listener.subscribe(cap)
        self.game.handle_bank()
        # Unified hook model mutates parts pre-multiplier; pending_raw now reflects mutated total
        self.assertEqual(captured.get("pending_raw"), 100)
        self.assertEqual(captured.get("adjusted"), 100)
        score = captured.get("score")
        self.assertIsNotNone(score)
        if score:
            parts = score.get("parts", [])
            self.assertEqual(parts[0]["raw"], 50)
            self.assertEqual(parts[0]["adjusted"], 100)

    def test_two_fives_flat_bonus(self):
        # Two separate single locks of fives should each get +50 flat => total raw 100 -> adjusted 200
        for i,d in enumerate(self.game.dice):
            d.value = 5 if i < 2 else 2
            d.held = False
            d.selected = False
        self.game.mark_scoring_dice()
        # Lock each five individually
        for idx in range(2):
            for d in self.game.dice:
                d.selected = False
            self.game.dice[idx].selected = True
            self.game.handle_lock()
        captured = {}
        def cap(ev):
            if ev.type == GameEventType.SCORE_APPLIED:
                captured.update(ev.payload)
        self.game.event_listener.subscribe(cap)
        self.game.handle_bank()
        self.assertEqual(captured.get("pending_raw"), 200)
        self.assertEqual(captured.get("adjusted"), 200)
        score = captured.get("score", {})
        if score:
            parts = score.get("parts", [])
            self.assertEqual(parts[0]["raw"], 100)
            self.assertEqual(parts[0]["adjusted"], 200)

if __name__ == '__main__':
    unittest.main()
