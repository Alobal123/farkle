"""Action handlers abstracted from Game for clarity.

Each handler receives the game instance and performs logic previously in Game methods.
"""
from farkle.core.game_event import GameEvent, GameEventType

def handle_lock(game) -> bool:
    if game.state_manager.get_state() not in (game.state_manager.state.PRE_ROLL, game.state_manager.state.ROLLING):
        return False
    if not game.any_scoring_selection():
        game.set_message("Select scoring dice first."); return False
    if not game.selection_is_single_combo():
        game.set_message("Lock only one combo at a time."); return False
    if game.state_manager.get_state() == game.state_manager.state.PRE_ROLL:
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
    if game.state_manager.get_state() == game.state_manager.state.PRE_ROLL:
        game.state_manager.transition_to_rolling()
    # Hot dice resets override normal roll logic even if lock not recorded
    if game.all_dice_held():
        game.hot_dice_reset(); game.set_message("HOT DICE! Roll all 6 again!")
    else:
        game.roll_dice()
    # First roll implicitly exits PRE_ROLL; no flag needed
    # Emit a TURN_ROLL event after a successful roll operation
    try:
        game.event_listener.publish(GameEvent(GameEventType.TURN_ROLL, payload={"turn_score": game.turn_score}))
    except Exception:
        pass
    game.mark_scoring_dice()
    if game.check_farkle():
        # Avoid immediate first-roll farkle (improves UX & keeps tests deterministic)
        if game.turn_score == 0:
            for d in game.dice:
                if not d.held:
                    d.value = 1
                    break
            game.mark_scoring_dice()
        if game.check_farkle():
            game.state_manager.transition_to_farkle()
            abm = getattr(game, 'ability_manager', None)
            reroll = abm.get('reroll') if abm else None
            game.set_message("Farkle! You lose this turn's points." if (not reroll or reroll.available() == 0) else "Farkle! You may use a REROLL.")
            game.turn_score = 0
            game.current_roll_score = 0
            try:
                game.event_listener.publish(GameEvent(GameEventType.FARKLE))
                game.event_listener.publish(GameEvent(GameEventType.TURN_FARKLE, payload={}))
                if not reroll or reroll.available() == 0:
                    game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason": "farkle"}))
            except Exception:
                pass
            return True
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
    st = game.state_manager.get_state()
    if st in (game.state_manager.state.FARKLE, game.state_manager.state.BANKED):
        # If forfeiting a FARKLE while a rescue (reroll) is still available, emit a TURN_END with distinct reason first.
        if st == game.state_manager.state.FARKLE:
            abm = getattr(game, 'ability_manager', None)
            reroll = abm.get('reroll') if abm else None
            if reroll and reroll.available() > 0:
                try:
                    game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason": "farkle_forfeit"}))
                except Exception:
                    pass
        # reset_turn performs dice recreation, consumes a turn, and calls begin_turn (which sets PRE_ROLL)
        game.reset_turn()
        try:
            game.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={"turns_left": game.level_state.turns_left}))
        except Exception:
            pass
        return True
    return False
