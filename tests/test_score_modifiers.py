import unittest, pygame
from game import Game
from settings import WIDTH, HEIGHT
from score_modifiers import ScoreMultiplier
from game_event import GameEvent, GameEventType

class ScoreModifierTests(unittest.TestCase):
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
        self.game.state_manager.transition_to_rolling()

    def test_multiplier_chain_applies(self):
        # Add an extra multiplier (total expected factor 1.0 * 1.5 = 1.5)
        self.game.player.add_modifier(ScoreMultiplier(mult=1.5))
        # Prepare a simple single scoring die (1 => 100 raw)
        d = self.game.dice[0]
        d.value = 1; d.selected = True; d.scoring_eligible = True
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        goal = self.game.level_state.goals[0]
        pre_remaining = goal.remaining
        self.game.handle_bank()
        # adjusted should be 100 * 1.5 = 150 (int cast should keep 150)
        self.assertEqual(pre_remaining - goal.remaining, 150)

    def test_event_sequence_unchanged(self):
        # Add a second multiplier for combined effect & capture events
        self.game.player.add_modifier(ScoreMultiplier(mult=2.0))
        captured = []
        def cap(ev):
            if ev.type in (GameEventType.SCORE_APPLY_REQUEST, GameEventType.SCORE_APPLIED, GameEventType.GOAL_PROGRESS):
                captured.append(ev.type)
        self.game.event_listener.subscribe(cap)
        d = self.game.dice[0]
        d.value = 1; d.selected = True; d.scoring_eligible = True
        self.assertTrue(self.game._auto_lock_selection("Locked"))
        self.game.handle_bank()
        self.assertGreaterEqual(len(captured), 3)
        self.assertEqual(captured[0], GameEventType.SCORE_APPLY_REQUEST)
        self.assertEqual(captured[1], GameEventType.SCORE_APPLIED)
        self.assertEqual(captured[2], GameEventType.GOAL_PROGRESS)

if __name__ == '__main__':
    unittest.main()
