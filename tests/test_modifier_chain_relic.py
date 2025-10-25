import unittest
from unittest.mock import Mock
from farkle.relics.relic import Relic
from farkle.scoring.score_modifiers import RuleSpecificMultiplier, FlatRuleBonus
from farkle.scoring.score_types import Score, ScorePart

class TestModifierChainRelic(unittest.TestCase):
    def test_relic_modifiers_compose_selectively(self):
        # Create a relic with both a rule-specific multiplier and a flat bonus
        relic = Relic(id="hybrid", name="Hybrid Relic", cost=0, description="A hybrid relic.")
        relic.add_modifier(RuleSpecificMultiplier(rule_key="SingleValue:1", mult=2.0))
        relic.add_modifier(FlatRuleBonus(rule_key="SingleValue:5", amount=50))
        # Build a Score with one SingleValue:1 (100) and one SingleValue:5 (50)
        score = Score(parts=[
            ScorePart(rule_key="SingleValue:1", raw=100),
            ScorePart(rule_key="SingleValue:5", raw=50),
        ])
        
        mock_context = Mock()
        mock_context.score_obj = score
        mock_context.goal = None

        # Apply just the relic's modifier chain selectively
        adjusted = relic.modifier_chain.apply(score.total_raw, mock_context)
        # Expect: 1s doubled -> 200; 5s +50 -> 100; total 300
        self.assertEqual(adjusted, 300)

if __name__ == '__main__':
    unittest.main()
