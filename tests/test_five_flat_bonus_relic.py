import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from game_event import GameEvent, GameEventType

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
        self.game = Game(self.screen, self.font, self.clock)
        # Give player enough gold to buy (30)
        self.game.player.gold = 30
        # Simulate end of level 1 to open shop (level_index starts at 1 so emulate advance finish)
        from game_event import GameEventType as GET, GameEvent as GE
        self.game.event_listener.publish(GE(GET.LEVEL_ADVANCE_FINISHED, payload={"level_index":1}))
        # Ensure offer is the Charm of Fives
        self.assertTrue(self.game.relic_manager.current_offer)
        self.assertIn("Charm of Fives", self.game.relic_manager.current_offer.relic.name)
        # Purchase
        self.game.event_listener.publish(GE(GET.REQUEST_BUY_RELIC, payload={}))

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
        # Raw should be 50 + flat 50 -> adjusted 100
        self.assertEqual(captured.get("pending_raw"), 50)
        self.assertEqual(captured.get("adjusted"), 100)
        score = captured.get("score")
        self.assertIsNotNone(score)
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
        self.assertEqual(captured.get("pending_raw"), 100)
        self.assertEqual(captured.get("adjusted"), 200)
        parts = captured.get("score", {}).get("parts", [])
        self.assertEqual(parts[0]["raw"], 100)
        self.assertEqual(parts[0]["adjusted"], 200)

if __name__ == '__main__':
    unittest.main()
