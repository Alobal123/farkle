import pytest
from farkle.scoring.scoring import ScoringRules, ThreeOfAKind, FourOfAKind, FiveOfAKind, SixOfAKind, SingleValue, Straight1to5, Straight2to6, Straight6


def build_rules():
    rules = ScoringRules()
    base = {1:1000,2:200,3:300,4:400,5:500,6:600}
    for v, pts in base.items():
        rules.add_rule(ThreeOfAKind(v, pts))
        rules.add_rule(FourOfAKind(v, pts))
        rules.add_rule(FiveOfAKind(v, pts))
        rules.add_rule(SixOfAKind(v, pts))
    rules.add_rule(SingleValue(1,100))
    rules.add_rule(SingleValue(5,50))
    rules.add_rule(Straight6(1500))
    rules.add_rule(Straight1to5(1000))
    rules.add_rule(Straight2to6(1000))
    return rules

@pytest.mark.parametrize("value,three_pts,mult,count", [
    (2,200,2,4),
    (3,300,3,5),
    (5,500,4,6),
])
def test_n_of_a_kind_scaling(value, three_pts, mult, count):
    # Generate EXACT count of the value plus neutral fillers that are not scoring singles (avoid 1 and 5)
    dice = [value] * count
    filler_candidates = [x for x in range(2,7) if x != value and x not in (1,5)]
    fi = 0
    while len(dice) < 6:
        dice.append(filler_candidates[fi % len(filler_candidates)])
        fi += 1
    rules = build_rules()
    total, used, breakdown = rules.evaluate(dice)
    expected = three_pts * mult  # highest applicable n-of-a-kind bonus only
    assert total == expected, f"Expected {expected} for {count} of {value}, got {total} (dice={dice}, breakdown={breakdown})"


def test_partial_straight_1_to_5():
    dice = [1,2,3,4,5]
    rules = build_rules()
    total, used, breakdown = rules.evaluate(dice)
    assert total == 1000
    assert any(k == 'Straight1to5' for k,_ in breakdown)


def test_partial_straight_2_to_6():
    dice = [2,3,4,5,6]
    rules = build_rules()
    total, used, breakdown = rules.evaluate(dice)
    assert total == 1000
    assert any(k == 'Straight2to6' for k,_ in breakdown)


def test_full_straight_prioritization():
    # Full straight should give 1500 not 1000 (no 1-5 or 2-6 since 6 dice present)
    dice = [1,2,3,4,5,6]
    rules = build_rules()
    total, used, breakdown = rules.evaluate(dice)
    assert total == 1500
    assert any(k == 'Straight6' for k,_ in breakdown)
    assert not any(k in ('Straight1to5','Straight2to6') for k,_ in breakdown)
