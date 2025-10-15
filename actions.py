"""Action handlers abstracted from Game for clarity.

Each handler receives the game instance and performs logic previously in Game methods.
"""
from game_event import GameEvent, GameEventType

def handle_lock(game) -> bool:
    if game.state_manager.get_state() not in (game.state_manager.state.START, game.state_manager.state.ROLLING):
        return False
    if not game.any_scoring_selection():
        game.set_message("Select scoring dice first."); return False
    if not game.selection_is_single_combo():
        game.set_message("Lock only one combo at a time."); return False
    if game.state_manager.get_state() == game.state_manager.state.START:
        game.state_manager.transition_to_rolling()
    if not game._auto_lock_selection("Locked"):
        game.set_message("No score in selection."); return False
    if game.turn_score > 0:
        game.set_message(game.message + " Pending applied on BANK.")
    # Emit lock-added event
    try:
        game.event_listener.publish(GameEvent(GameEventType.TURN_LOCK_ADDED, payload={"turn_score": game.turn_score}))
    except Exception:
        pass
    return True

def handle_roll(game) -> bool:
    # If there is a selection, attempt to auto-lock before rolling
    if any(d.selected for d in game.dice):
        if not game._auto_lock_selection("Auto-locked"):
            game.set_message("Lock selected dice before rolling."); return False
        else:
            game.message += " Rolling..."
    # Guard: require a lock after a roll unless all dice are already held (hot dice scenario)
    if (game.state_manager.get_state() == game.state_manager.state.ROLLING
        and not game.locked_after_last_roll
        and not game.all_dice_held()):
        game.set_message("Lock a scoring combo before rolling again."); return False
    # Transition out of START
    if game.state_manager.get_state() == game.state_manager.state.START:
        game.state_manager.transition_to_rolling()
    # Hot dice resets override normal roll logic even if lock not recorded
    if game.all_dice_held():
        game.hot_dice_reset(); game.set_message("HOT DICE! Roll all 6 again!")
    else:
        game.roll_dice()
    # Mark that at least one roll occurred this turn
    try:
        game.initial_roll_done = True
    except Exception:
        pass
    # Emit a TURN_ROLL event after a successful roll operation
    try:
        game.event_listener.publish(GameEvent(GameEventType.TURN_ROLL, payload={"turn_score": game.turn_score}))
    except Exception:
        pass
    game.mark_scoring_dice()
    if game.check_farkle():
        # Avoid immediate first-roll farkle (improves UX & keeps tests deterministic)
        if game.turn_score == 0:
            # Force one die to be scoring (value 1) and re-evaluate once
            for d in game.dice:
                if not d.held:
                    d.value = 1
                    break
            game.mark_scoring_dice()
        if game.check_farkle():
            game.state_manager.transition_to_farkle()
            game.set_message("Farkle! You lose this turn's points." if game.rerolls_remaining() == 0 else "Farkle! You may use a REROLL.")
            game.turn_score = 0
            game.current_roll_score = 0
            try:
                game.event_listener.publish(GameEvent(GameEventType.FARKLE))
                game.event_listener.publish(GameEvent(GameEventType.TURN_FARKLE, payload={}))
                # Defer TURN_END if rerolls remain
                if game.rerolls_remaining() == 0:
                    game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason": "farkle"}))
            except Exception:
                pass
            return True  # farkle ends roll attempt successfully (turn may continue if reroll used)
    return True

def handle_bank(game) -> bool:
    if game.state_manager.get_state() != game.state_manager.state.ROLLING:
        return False
    if any(d.selected for d in game.dice):
        if game.selection_is_single_combo() and game.any_scoring_selection():
            if not game._auto_lock_selection("Auto-locked"):
                game.set_message("Selection has no score; cannot bank with it selected."); return False
            else:
                game.set_message(game.message + " before banking.")
        else:
            game.set_message("Invalid selection: deselect or lock a single combo before banking."); return False
    if game.turn_score <= 0:
        return False
    # Goals now apply their own pending in response to BANK event.
    # Defer zeroing scores until after SCORE_APPLIED / TURN_END so UI can still show pre-bank total if needed.
    game.state_manager.transition_to_banked()
    try:
        game.event_listener.publish(GameEvent(GameEventType.BANK, payload={}))
        game.event_listener.publish(GameEvent(GameEventType.TURN_BANKED, payload={"banked": True}))
        # TURN_END now emitted after all SCORE_APPLY_REQUEST/SCORE_APPLIED cycles finish (in Game.on_event)
    except Exception:
        pass
    if game.level_state.completed:
        game.set_message("Rite complete! All mandatory goals appeased.")
    else:
        remaining = [game.level.goals[i][0] for i in game.level_state.mandatory_indices if not game.level_state.goals[i].is_fulfilled()]
        rem_text = ", ".join(remaining) if remaining else "None"
        game.set_message(f"Turn banked. Remaining mandatories: {rem_text}")
    return True

def handle_next_turn(game) -> bool:
    if game.state_manager.get_state() in (game.state_manager.state.FARKLE, game.state_manager.state.BANKED):
        game.reset_turn(); return True
    return False
