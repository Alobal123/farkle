import pygame
import pytest
from game import Game
from level import Level

@pytest.mark.parametrize("bank_path", [True])
def test_dice_reset_between_turns(bank_path):
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()
    g = Game(screen, font, clock, level=Level.single("Test", target_goal=150, max_turns=3, description=""))

    # First roll
    assert g.state_manager.get_state().name == 'PRE_ROLL'
    from actions import handle_roll, handle_lock, handle_bank, handle_next_turn
    handle_roll(g)
    # Try to create a scoring lock path then bank; perform up to two roll cycles
    for _ in range(2):
        if g.any_scoring_selection() and g.selection_is_single_combo():
            handle_lock(g)
        if g.turn_score > 0:
            handle_bank(g)
            break
        # If still rolling and no bank yet, roll again
        if g.state_manager.get_state().name == 'ROLLING':
            handle_roll(g)
    # If still rolling with no score, simulate a farkle by zeroing and forcing transition
    if g.state_manager.get_state().name == 'ROLLING' and g.turn_score == 0:
        # Force farkle-style end
        g.state_manager.transition_to_farkle()
    assert g.state_manager.get_state().name in ('BANKED','FARKLE')
    handle_next_turn(g)
    assert g.state_manager.get_state().name == 'PRE_ROLL'

    # Capture die objects references (should be freshly re-created)
    new_dice = list(g.dice)
    assert all(not d.held for d in new_dice), "Expected all dice to be unheld at start of new turn"
    assert all(not d.selected for d in new_dice), "Expected all dice unselected at new turn start"

    # Roll second turn
    handle_roll(g)
    assert g.state_manager.get_state().name == 'ROLLING'
    # None of the dice should be erroneously held unless scoring flow locks them this turn
    assert all(not d.held for d in g.dice), "Dice carried held state into new turn incorrectly"
