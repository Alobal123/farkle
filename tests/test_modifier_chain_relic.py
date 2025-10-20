import unittest
from farkle.relics.relic import Relic
from farkle.scoring.score_modifiers import RuleSpecificMultiplier, FlatRuleBonus
from farkle.scoring.score_types import Score, ScorePart

class TestModifierChainRelic(unittest.TestCase):
    def test_relic_modifiers_compose_selectively(self):
        # Create a relic with both a rule-specific multiplier and a flat bonus
        relic = Relic(name="Hybrid Relic")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:1", mult=2.0))
        relic.add_modifier(FlatRuleBonus(rule_key="SingleValue:5", amount=50))
        # Build a Score with one SingleValue:1 (100) and one SingleValue:5 (50)
        score = Score(parts=[
            ScorePart(rule_key="SingleValue:1", raw=100),
            ScorePart(rule_key="SingleValue:5", raw=50),
        ])
        class Ctx:
            def __init__(self, s):
                self.pending_raw = s.total_raw
                self.score_obj = s
        ctx = Ctx(score)
        # Apply just the relic's modifier chain selectively
        adjusted = relic.modifier_chain.apply(score.total_raw, ctx)
        # Expect: 1s doubled -> 200; 5s +50 -> 100; total 300
        self.assertEqual(adjusted, 300)

if __name__ == '__main__':
    unittest.main()
