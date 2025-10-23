import pytest
import pygame
from farkle.relics.relic import OptionalFocusCharm
from tests.test_helpers import ensure_relic_modifiers
from farkle.game import Game

@pytest.mark.parametrize("dice_values,raw_expected,adjusted_expected", [([1], 100, 120)])
def test_optional_focus_charm_affects_selection_preview(dice_values, raw_expected, adjusted_expected):
    # Create game instance via existing demo-level factory (simplify: use Game directly)
    # Initialize pygame font system (safe for tests)
    try:
        pygame.init()
    except Exception:
        pass
    screen = pygame.Surface((800, 600))
    font = pygame.font.Font(None, 24)
    class DummyClock:  # minimal clock stub
        def tick(self, fps):
            return 0
    clock = DummyClock()
    g = Game(screen, font, clock)
    # Ensure we have at least one optional goal; convert first goal to optional for test if needed.
    try:
        goals = g.level_state.goals
        if goals:
            # Force active goal index 0
            g.active_goal_index = 0
            goals[0].mandatory = False  # mark optional
    except Exception:
        pytest.skip("Game level_state goals not available")

    # Purchase the optional focus charm analog: add its modifier directly
    relic = OptionalFocusCharm()
    ensure_relic_modifiers(g, [relic])
    # Now perform a dice roll setup: inject dice values manually
    # Replace dice values and scoring selection state
    container = g.dice_container
    # Set dice to desired values and mark scoring selection for one combo (simulate selecting all scoring dice)
    # Clear existing selection state first
    for d in container.dice:
        d.selected = False
        d.held = False
    # Assign desired dice values to first len(dice_values) dice; select only those forming single combo
    for i, dval in enumerate(dice_values):
        container.dice[i].value = dval
        container.dice[i].selected = True
    # Let container recompute scoring flags if method exists
    try:
        container.mark_scoring()
    except Exception:
        pass
    # Ensure selection constitutes exactly one scoring combo (matched rule key)
    rk = None
    try:
        rk = container.selection_rule_key()
    except Exception:
        rk = None
    assert rk is not None, "Selection did not produce a single rule key"
    # Use selection_preview
    raw, adj_preview, final_preview, mult = g.selection_preview()
    assert raw == raw_expected
    assert adj_preview == adjusted_expected
    assert final_preview == adjusted_expected
    assert mult == 1.0
