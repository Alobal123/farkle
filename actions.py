"""Action handlers abstracted from Game for clarity.

Each handler receives the game instance and performs logic previously in Game methods.
"""
from typing import Any

def handle_lock(game):
    if game.state_manager.get_state() not in (game.state_manager.state.START, game.state_manager.state.ROLLING):
        return
    if not game.any_scoring_selection():
        game.set_message("Select scoring dice first."); return
    if not game.selection_is_single_combo():
        game.set_message("Lock only one combo at a time."); return
    if game.state_manager.get_state() == game.state_manager.state.START:
        game.state_manager.transition_to_rolling()
    if not game._auto_lock_selection("Locked"):
        game.set_message("No score in selection."); return
    if game.turn_score > 0:
        game.set_message(game.message + " Pending applied on BANK.")

def handle_roll(game):
    if any(d.selected for d in game.dice):
        if not game._auto_lock_selection("Auto-locked"):
            game.set_message("Lock selected dice before rolling."); return
        else:
            game.message += " Rolling..."
    if game.state_manager.get_state() == game.state_manager.state.ROLLING and not game.locked_after_last_roll:
        game.set_message("Lock a scoring combo before rolling again."); return
    if game.state_manager.get_state() == game.state_manager.state.START:
        game.state_manager.transition_to_rolling()
    if game.all_dice_held():
        game.hot_dice_reset(); game.set_message("HOT DICE! Roll all 6 again!")
    else:
        game.roll_dice()
    game.mark_scoring_dice()
    if game.check_farkle():
        game.state_manager.transition_to_farkle()
        game.set_message("Farkle! You lose this turn's points.")
        game.turn_score = 0
        game.current_roll_score = 0

def handle_bank(game):
    if game.state_manager.get_state() != game.state_manager.state.ROLLING:
        return
    if any(d.selected for d in game.dice):
        if game.selection_is_single_combo() and game.any_scoring_selection():
            if not game._auto_lock_selection("Auto-locked"):
                game.set_message("Selection has no score; cannot bank with it selected."); return
            else:
                game.set_message(game.message + " before banking.")
        else:
            game.set_message("Invalid selection: deselect or lock a single combo before banking."); return
    if game.turn_score <= 0:
        return
    for g_idx, raw_points in game.pending_goal_scores.items():
        goal_obj = game.level_state.goals[g_idx]
        pre_remaining = goal_obj.get_remaining()
        game.level_state.apply_score(g_idx, raw_points)
        if goal_obj.is_fulfilled() and pre_remaining > 0:
            gained = goal_obj.claim_reward()
            if gained:
                game.player.add_gold(gained)
                game.set_message(f"{game.message} +{gained} gold")
    game.turn_score = 0
    game.current_roll_score = 0
    game.state_manager.transition_to_banked()
    game.pending_goal_scores.clear()
    if game.level_state.completed:
        game.set_message("Rite complete! All mandatory goals appeased.")
    else:
        remaining = [game.level.goals[i][0] for i in game.level_state.mandatory_indices if not game.level_state.goals[i].is_fulfilled()]
        rem_text = ", ".join(remaining) if remaining else "None"
        game.set_message(f"Turn banked. Remaining mandatories: {rem_text}")

def handle_next_turn(game):
    if game.state_manager.get_state() in (game.state_manager.state.FARKLE, game.state_manager.state.BANKED):
        game.reset_turn()
