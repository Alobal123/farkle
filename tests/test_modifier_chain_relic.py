import unittest
from dataclasses import dataclass
from player import Player
from relic import Relic
from score_modifiers import ScoreModifierChain

class TestModifierChainRelic(unittest.TestCase):
    def test_player_and_relic_multipliers_stack(self):
        p = Player()
        # Player starts with 1.0 multiplier
        relic = Relic(name="Relic of Fortune", base_multiplier=1.5)
        # Simulate progression adding +0.2 to player (results in 1.2)
        p.add_score_multiplier(0.2)
        base = 100
        # Player adjusted using own chain
        @dataclass
        class Ctx:
            pending_raw: int
        context = Ctx(pending_raw=base)
        player_only = p.modifier_chain.apply(base, context)
        self.assertEqual(player_only, 120)  # 100 * 1.2
        # Combined (manual aggregation of chains for now)
        combined_chain = ScoreModifierChain(list(p.modifier_chain.snapshot()) + list(relic.modifier_chain.snapshot()))
        combined = combined_chain.apply(base, context)
        # Expect 100 * 1.2 * 1.5 = 180
        self.assertEqual(combined, 180)

if __name__ == '__main__':
    unittest.main()
