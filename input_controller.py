from game_event import GameEvent, GameEventType

class InputController:
    """Listens for REQUEST_* events, validates state, invokes domain actions, and publishes
    either the resulting domain event (ROLL/LOCK/BANK) or REQUEST_DENIED/MESSAGE.
    """
    def __init__(self, game):
        self.game = game

    def on_event(self, event: GameEvent):  # type: ignore[override]
        t = event.type
        g = self.game
        if t == GameEventType.REQUEST_ROLL:
            self._handle_roll_request()
        elif t == GameEventType.REQUEST_LOCK:
            self._handle_lock_request()
        elif t == GameEventType.REQUEST_BANK:
            self._handle_bank_request()
        elif t == GameEventType.REQUEST_NEXT_TURN:
            self._handle_next_turn_request()

    # Internal handlers
    def _emit(self, etype: GameEventType, payload=None):
        self.game.event_listener.publish(GameEvent(etype, payload=payload or {}))

    def _deny(self, reason: str):
        self._emit(GameEventType.REQUEST_DENIED, {"reason": reason})
        self._emit(GameEventType.MESSAGE, {"text": reason})
        self.game.set_message(reason)

    def _handle_roll_request(self):
        g = self.game
        current_state = g.state_manager.get_state()
        valid_combo_selected = g.selection_is_single_combo() and g.any_scoring_selection()
        can_roll = (current_state == g.state_manager.state.START) or (current_state == g.state_manager.state.ROLLING and (g.locked_after_last_roll or valid_combo_selected))
        if not can_roll:
            self._deny("Lock a scoring combo before rolling again."); return
        g.handle_roll()
        self._emit(GameEventType.ROLL, {"turn_score": g.turn_score})

    def _handle_lock_request(self):
        g = self.game
        before = g.turn_score
        g.handle_lock()
        if g.turn_score == before:  # No change
            # g.handle_lock sets message already
            self._deny(g.message)
        else:
            self._emit(GameEventType.LOCK, {"turn_score": g.turn_score, "goal_index": g.active_goal_index})

    def _handle_bank_request(self):
        g = self.game
        if g.turn_score <= 0:
            self._deny("No points to bank."); return
        g.handle_bank()
        self._emit(GameEventType.BANK, {})

    def _handle_next_turn_request(self):
        g = self.game
        g.handle_next_turn()
        self._emit(GameEventType.TURN_START, {"turns_left": g.level_state.turns_left})
