import pytest

from farkle.scoring.scoring_manager import ScoringManager
from farkle.goals.goal import Goal
from farkle.relics.relic import MandatoryFocusTalisman, OptionalFocusCharm
from farkle.scoring.score_modifiers import FlatRuleBonus
from farkle.core.game_object import GameObject

class DummyGame(GameObject):
    def __init__(self):
        super().__init__(name="DG")
        self.rules = DummyRules()
        self.event_listener = DummyEventListener()
        self.level_index = 0
        self.player = type("P", (), {"gold": 999})()
        self.scoring_manager = ScoringManager(self)

    def draw(self, surface):
        return None

class DummyEventListener:
    def publish(self, event):
        pass
    def publish_immediate(self, event):
        pass
    def subscribe(self, cb):
        pass

class DummyRules:
    def evaluate(self, dice_values):
        # Minimal scoring: each 1 -> 100, each 5 -> 50
        total = 0
        used = []
        breakdown = []
        ones = sum(1 for d in dice_values if d == 1)
        fives = sum(1 for d in dice_values if d == 5)
        if ones:
            pts = ones * 100
            breakdown.append(("SingleValue:1", pts))
            total += pts
        if fives:
            pts = fives * 50
            breakdown.append(("SingleValue:5", pts))
            total += pts
        used = [d for d in dice_values if d in (1,5)]
        return total, used, breakdown

@pytest.fixture
def game():
    return DummyGame()

@pytest.fixture
def scoring_mgr(game):
    return game.scoring_manager


def build_parts(scoring_mgr, dice):
    comp = scoring_mgr.compute_from_dice(dice)
    return [(p['rule_key'], p['raw']) for p in comp['parts']], comp


def test_mandatory_focus_talisman_only_on_mandatory_goal(scoring_mgr):
    relic = MandatoryFocusTalisman()
    # Activate by adding modifier chain directly (simulate purchase)
    scoring_mgr.modifier_chain.add(relic.modifier_chain.snapshot()[0])
    mandatory_goal = Goal(target_score=1000, name="M", mandatory=True)
    optional_goal = Goal(target_score=1000, name="O", mandatory=False)
    parts, comp = build_parts(scoring_mgr, [1,5])  # raw 150
    base_raw = comp['total_raw']
    assert base_raw == 150
    prev_mandatory = scoring_mgr.preview(parts, goal=mandatory_goal)
    prev_optional = scoring_mgr.preview(parts, goal=optional_goal)
    # 20% boost applied only to mandatory goal: 150 *1.2 = 180
    assert prev_mandatory['adjusted_total'] == 180
    assert prev_optional['adjusted_total'] == 150


def test_optional_focus_charm_only_on_optional_goal(scoring_mgr):
    relic = OptionalFocusCharm()
    scoring_mgr.modifier_chain.add(relic.modifier_chain.snapshot()[0])
    mandatory_goal = Goal(target_score=1000, name="M", mandatory=True)
    optional_goal = Goal(target_score=1000, name="O", mandatory=False)
    parts, comp = build_parts(scoring_mgr, [1,1,5])  # raw 250
    base_raw = comp['total_raw']
    assert base_raw == 250
    prev_optional = scoring_mgr.preview(parts, goal=optional_goal)
    prev_mandatory = scoring_mgr.preview(parts, goal=mandatory_goal)
    assert prev_optional['adjusted_total'] == 300  # 250 *1.2
    assert prev_mandatory['adjusted_total'] == 250
