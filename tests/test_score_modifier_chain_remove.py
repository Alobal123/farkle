import unittest
from farkle.scoring.score_modifiers import ScoreModifierChain, FlatAddEffect, RuleKeyMatcher, CompositePartModifier
from farkle.scoring.score_types import Score, ScorePart

class DummyFlat(CompositePartModifier):
    def __init__(self, rule_key: str, amount: int):
        super().__init__(matcher=RuleKeyMatcher(rule_key), effect=FlatAddEffect(amount), priority=60)
        self.rule_key = rule_key
        self.amount = amount

class ScoreModifierChainRemoveTests(unittest.TestCase):
    def test_remove_by_identity(self):
        chain = ScoreModifierChain()
        m1 = DummyFlat('SingleValue:5', 50)
        m2 = DummyFlat('SingleValue:1', 100)
        chain.add(m1)
        chain.add(m2)
        removed = chain.remove_by_identity('DummyFlat', {'rule_key':'SingleValue:5','amount':50})
        self.assertTrue(removed)
        # Remaining should be m2 only
        self.assertEqual(len(chain.snapshot()), 1)
        self.assertEqual(getattr(chain.snapshot()[0], 'rule_key', None), 'SingleValue:1')

if __name__ == '__main__':
    unittest.main()
