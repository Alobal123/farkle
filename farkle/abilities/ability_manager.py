from __future__ import annotations
from typing import List, Optional
from farkle.abilities.ability import Ability, RerollAbility, TargetedAbility
from farkle.core.game_event import GameEventType

class AbilityManager:
    def __init__(self, game):
        self.game = game
        self.abilities: List[Ability] = []
        # Register default abilities
        self.register(RerollAbility())
        # Track last auto-executed single-target ability for finalize_selection semantics
        self._last_auto_target: Ability | None = None

    def activate_all(self):
        """Activate all abilities subscribing each to its charge modification event."""
        for a in self.abilities:
            try:
                self.game.event_listener.subscribe(a.on_event, types={GameEventType.ABILITY_CHARGES_ADDED, GameEventType.ABILITY_TARGETS_ADDED})
            except Exception:
                pass

    def register(self, ability: Ability):
        self.abilities.append(ability)
        # If event listener already present (e.g., in lightweight DummyGame), subscribe immediately
        el = getattr(self.game, 'event_listener', None)
        if el is not None:
            try:
                el.subscribe(ability.on_event, types={GameEventType.ABILITY_CHARGES_ADDED, GameEventType.ABILITY_TARGETS_ADDED})
            except Exception:
                pass
        # Emit ABILITY_REGISTERED event so UI can rebuild buttons
        if el is not None:
            try:
                from farkle.core.game_event import GameEvent
                el.publish(GameEvent(GameEventType.ABILITY_REGISTERED, payload={"ability_id": ability.id, "ability_name": ability.name}))
            except Exception:
                pass

    def reset_level(self):
        for a in self.abilities:
            a.reset_level()

    def get(self, ability_id: str) -> Optional[Ability]:
        for a in self.abilities:
            if a.id == ability_id:
                return a
        return None

    def ability_buttons(self) -> List[Ability]:
        return self.abilities

    def toggle_or_execute(self, ability_id: str):
        ability = self.get(ability_id)
        if not ability:
            return False
        prev_selecting = ability.selecting
        started = ability.begin(self)
        # Reset executed_once flag on new activation for TargetedAbility so subsequent charges work
        if started and isinstance(ability, TargetedAbility):
            ability.executed_once = False
        # Handle state transitions when entering/exiting selection mode
        if ability.selectable:
            if not prev_selecting and ability.selecting:
                # Enter selecting state
                try:
                    self.game.state_manager.enter_selecting_targets()
                except Exception:
                    pass
                try:
                    from farkle.core.game_event import GameEvent, GameEventType
                    self.game.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_STARTED, payload={"ability": ability.id}))
                except Exception:
                    pass
            elif prev_selecting and not ability.selecting:
                # Exited selection (either executed or cancelled)
                # Restoration handled by state manager using stored prior play state
                try:
                    self.game.state_manager.exit_selecting_targets()
                except Exception:
                    pass
                try:
                    from farkle.core.game_event import GameEvent, GameEventType
                    self.game.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_FINISHED, payload={"ability": ability.id}))
                    # If the ability just rescued a farkle, ensure message persists
                    if ability.id == 'reroll' and self.game.state_manager.get_state().name == 'ROLLING' and 'rescued' not in getattr(self.game, 'message','').lower():
                        # Message safeguard (rare race condition)
                        self.game.set_message('Farkle rescued by reroll! Continue.')
                except Exception:
                    pass
        return started

    def is_selecting(self) -> bool:
        return any(a.selecting for a in self.abilities)

    def selecting_ability(self) -> Optional[Ability]:
        for a in self.abilities:
            if a.selecting:
                return a
        return None

    def attempt_target(self, target_type: str, target_index: int) -> bool:
        a = self.selecting_ability()
        if not a or not a.selecting:
            return False
        if a.target_type != target_type:
            return False
        # Multi-target accumulation logic
        if isinstance(a, TargetedAbility) and a.targets_needed > 1:
            # Toggle selection: add if absent, remove if present
            if target_index in a.collected_targets:
                a.collected_targets.remove(target_index)
            else:
                # Enforce capacity
                if len(a.collected_targets) >= a.targets_needed:
                    # Provide feedback instead of adding
                    try:
                        self.game.set_message(f"Already selected {a.targets_needed} dice for {a.name}. Right-click to reroll or deselect.")
                    except Exception:
                        pass
                    return True
                a.collected_targets.append(target_index)
            # Provide UI feedback without auto-executing; right-click will finalize
            try:
                remaining = max(0, a.targets_needed - len(a.collected_targets))
                # Allow early finalize with fewer than required (streamlined) but message should reflect optional second target
                if a.targets_needed > 1 and len(a.collected_targets) == 1:
                    self.game.set_message(f"Selected 1 die for {a.name}. Optionally select another or right-click to confirm.")
                else:
                    if remaining > 0:
                        self.game.set_message(f"Selected {len(a.collected_targets)}/{a.targets_needed} dice for {a.name}. Right-click to reroll or continue selecting.")
                    else:
                        self.game.set_message(f"Selected {len(a.collected_targets)}/{a.targets_needed} dice for {a.name}. Right-click to reroll or deselect.")
            except Exception:
                pass
            return True
        else:
            # Single-target behaves like multi: toggle selection only (if targeted ability)
            if isinstance(a, TargetedAbility):
                if target_index in a.collected_targets:
                    a.collected_targets.remove(target_index)
                else:
                    a.collected_targets.clear()
                    a.collected_targets.append(target_index)
                try:
                    if len(a.collected_targets) == 1:
                        self.game.set_message(f"1 die selected for {a.name}. Right-click to confirm.")
                    else:
                        self.game.set_message(f"No die selected for {a.name}.")
                except Exception:
                    pass
                return True
            return False

    def finalize_selection(self) -> bool:
        """Manually finalize multi-target selection (e.g., right-click submit)."""
        a = self.selecting_ability()
        if not a:
            return False
        if not isinstance(a, TargetedAbility):
            return False
        if not a.selecting:
            return False
        if len(a.collected_targets) == 0:
            return False
        # Streamlined: allow finalize with fewer than targets_needed (execute on collected set)
        executed = False
        if len(a.collected_targets) == 1:
            executed = a.execute(self, a.collected_targets[0])
        else:
            executed = a.execute(self, list(a.collected_targets))
        if executed:
            a.selecting = False
            try:
                self.game.state_manager.exit_selecting_targets()
            except Exception:
                pass
            try:
                from farkle.core.game_event import GameEvent, GameEventType
                self.game.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_FINISHED, payload={"ability": a.id, "targets": list(a.collected_targets)}))
                # After execution, re-evaluate farkle state if reroll ability used
                if a.id == 'reroll':
                    is_farkle_now = self.game.check_farkle()
                    underlying = getattr(self.game.state_manager.effective_play_state(), 'name', None)
                    if underlying == 'FARKLE' and not is_farkle_now:
                        try:
                            self.game.state_manager.rescue_farkle_to_rolling()
                        except Exception:
                            self.game.state_manager.transition_to_rolling()
                        self.game.set_message('Farkle rescued by reroll! Continue.')
                    elif underlying == 'ROLLING' and is_farkle_now:
                        try:
                            self.game.state_manager.transition_to_farkle()
                        except Exception:
                            pass
                        self.game.set_message('Farkle! No scoring dice after reroll.')
            except Exception:
                pass
            # Prepare for potential subsequent charge usage: clear collected targets
            a.collected_targets.clear()
            a.executed_once = False
        return executed
