import pytest

from farkle.scoring.score_modifiers import RuleSpecificMultiplier, MandatoryGoalOnly, OptionalGoalOnly
from farkle.scoring.scoring_manager import ScoringManager
from farkle.goals.goal import Goal
from farkle.core.game_object import GameObject

class DummyGame(GameObject):
    def __init__(self):
        super().__init__(name="DummyGame")
        self.rules = DummyRules()
        self.relic_manager = None  # tests won't use relic manager here

    def draw(self, surface):  # type: ignore[override]
        return None

class DummyRules:
    def evaluate(self, dice_values):
        # Return total, used dice list, breakdown list[(rule_key, raw)]
        # Simplified: treat each '1' as 100 points rule key 'ones', each '5' as 50 'fives'.
        total = 0
        used = []
        breakdown = []
        ones = sum(1 for d in dice_values if d == 1)
        fives = sum(1 for d in dice_values if d == 5)
        if ones:
            pts = ones * 100
            total += pts
            breakdown.append(("ones", pts))
        if fives:
            pts = fives * 50
            total += pts
            breakdown.append(("fives", pts))
        used = [d for d in dice_values if d in (1,5)]
        return total, used, breakdown

@pytest.fixture
def scoring_mgr():
    game = DummyGame()
    return ScoringManager(game)

class SimpleGoal(Goal):
    def __init__(self, mandatory: bool):
        # Provide a target_score; name; mandatory flag.
        super().__init__(target_score=500, name="G", mandatory=mandatory)
        # Minimal customization: attach game later only if needed.


def test_mandatory_goal_only_modifier_applies(scoring_mgr):
    # Create mandatory goal and optional goal
    mandatory_goal = SimpleGoal(mandatory=True)
    optional_goal = SimpleGoal(mandatory=False)
    # Build parts from dice manually (simulate selection preview via scoring rules)
    dice = [1,5]
    comp = scoring_mgr.compute_from_dice(dice)
    base_raw = comp['total_raw']
    assert base_raw == 150
    # Wrap a multiplier modifier that doubles 'ones' part only inside mandatory goal condition.
    inner = RuleSpecificMultiplier('ones', mult=2.0)
    conditional = MandatoryGoalOnly(inner)
    scoring_mgr.modifier_chain.add(conditional)
    # Preview with mandatory goal
    parts = [(p['rule_key'], p['raw']) for p in comp['parts']]
    preview_mandatory = scoring_mgr.preview(parts, goal=mandatory_goal)
    # 'ones' 100 doubled to 200; fives unchanged 50 -> total 250
    assert preview_mandatory['adjusted_total'] == 250
    # Preview with optional goal should ignore modifier
    preview_optional = scoring_mgr.preview(parts, goal=optional_goal)
    assert preview_optional['adjusted_total'] == 150


def test_optional_goal_only_modifier_applies(scoring_mgr):
    mandatory_goal = SimpleGoal(mandatory=True)
    optional_goal = SimpleGoal(mandatory=False)
    dice = [1,1,5]
    comp = scoring_mgr.compute_from_dice(dice)
    base_raw = comp['total_raw']
    assert base_raw == 250  # 2*100 + 50
    inner = RuleSpecificMultiplier('fives', mult=3.0)  # 50 -> 150 if applied
    conditional = OptionalGoalOnly(inner)
    scoring_mgr.modifier_chain.add(conditional)
    parts = [(p['rule_key'], p['raw']) for p in comp['parts']]
    preview_optional = scoring_mgr.preview(parts, goal=optional_goal)
    assert preview_optional['adjusted_total'] == 350  # 200 ones + 150 fives
    preview_mandatory = scoring_mgr.preview(parts, goal=mandatory_goal)
    assert preview_mandatory['adjusted_total'] == 250
