import pygame
import pytest
from farkle.game import Game
from farkle.relics.relic import OptionalFocusCharm, MandatoryFocusTalisman
from tests.test_helpers import ensure_relic_modifiers

@pytest.fixture
def game():
    try:
        pygame.init()
    except Exception:
        pass
    screen = pygame.Surface((800, 600))
    font = pygame.font.Font(None, 24)
    class DummyClock:
        def tick(self, fps):
            return 0
    return Game(screen, font, DummyClock())

def _single_combo_select(game, value: int):
    dc = game.dice_container
    for d in dc.dice:
        d.selected = False
        d.held = False
    dc.dice[0].value = value
    dc.dice[0].selected = True
    try:
        dc.mark_scoring()
    except Exception:
        pass

def test_helper_injects_and_is_idempotent(game):
    # Mark first goal optional to trigger OptionalFocusCharm effect
    game.active_goal_index = 0
    game.level_state.goals[0].mandatory = False
    opt = OptionalFocusCharm()
    mand = MandatoryFocusTalisman()
    ensure_relic_modifiers(game, [opt, mand])
    # Call again to ensure no duplicates
    ensure_relic_modifiers(game, [opt, mand])
    # Count occurrences of modifier classes
    names = [m.__class__.__name__ for m in game.scoring_manager.modifier_chain.snapshot()]
    assert names.count('OptionalGoalOnly') == 1
    assert names.count('MandatoryGoalOnly') == 1
    # Verify optional modifier applies with optional goal active (single die value 1 -> 100 raw -> 120 adjusted)
    _single_combo_select(game, 1)
    raw, adj1, adj2, mult = game.selection_preview()
    assert raw == 100
    assert adj1 == 120
    assert adj2 == 120
    # Switch to a mandatory goal (if exists) to verify mandatory boosts apply and optional does not
    game.level_state.goals[0].mandatory = True
    raw2_before, adj_mand1, adj_mand2, _ = game.selection_preview()
    # For mandatory goal we expect mandatory modifier to trigger (still 20%)
    assert raw2_before == 100
    assert adj_mand1 == 120
