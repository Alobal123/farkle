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
            if g.state_manager.get_state().name == 'SHOP':
                self._deny("Shop open: purchase or skip.")
            else:
                self._handle_roll_request()
        elif t == GameEventType.REQUEST_LOCK:
            if g.state_manager.get_state().name == 'SHOP':
                self._deny("Shop open: purchase or skip.")
            else:
                self._handle_lock_request()
        elif t == GameEventType.REQUEST_BANK:
            if g.state_manager.get_state().name == 'SHOP':
                self._deny("Shop open: purchase or skip.")
            else:
                self._handle_bank_request()
        elif t == GameEventType.REQUEST_NEXT_TURN:
            self._handle_next_turn_request()
        elif t == GameEventType.REQUEST_BUY_RELIC:
            # Handled by relic manager; nothing extra here
            pass
        elif t == GameEventType.REQUEST_SKIP_SHOP:
            pass
        elif t == GameEventType.REQUEST_REROLL:
            # Legacy event: map to generic ability request for 'reroll'
            self._handle_generic_ability_request('reroll')
        elif t == GameEventType.REQUEST_ABILITY:
            ability_id = event.get('id') or (event.payload.get('ability_id') if event.payload else None)
            if ability_id:
                self._handle_generic_ability_request(ability_id)
            else:
                self._deny("No ability id provided.")

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
        # If no accumulated turn_score yet but a valid single scoring selection exists, auto-lock it first
        if g.turn_score <= 0:
            if g.selection_is_single_combo() and g.any_scoring_selection():
                if not g._auto_lock_selection("Locked"):
                    self._deny("No points to bank."); return
                else:
                    # Successful auto-lock; proceed to bank if now positive
                    if g.turn_score <= 0:
                        self._deny("No points to bank."); return
            else:
                self._deny("No points to bank."); return
        g.handle_bank()
        self._emit(GameEventType.BANK, {})

    def _handle_next_turn_request(self):
        g = self.game
        g.handle_next_turn()
        self._emit(GameEventType.TURN_START, {"turns_left": g.level_state.turns_left})

    def _handle_generic_ability_request(self, ability_id: str):
        g = self.game
        mgr = getattr(g, 'ability_manager', None)
        if not mgr:
            self._deny("Abilities unavailable."); return
        ability = mgr.get(ability_id)
        if not ability:
            self._deny(f"Ability '{ability_id}' not found."); return
        if not ability.can_activate(mgr):
            self._deny(f"{ability.name} not available."); return
        started = mgr.toggle_or_execute(ability_id)
        # Mirror legacy reroll_selecting flag for tests if reroll ability
        if ability_id == 'reroll':
            try:
                self.game.reroll_selecting = bool(ability.selecting)
            except Exception:
                pass
        if ability.selectable:
            if ability.selecting:
                g.set_message(f"Select target(s) for {ability.name}.")
            else:
                # If selection cancelled without execution
                if ability.available() >= 0:  # state unchanged or executed
                    g.set_message(f"{ability.name} cancelled." )
