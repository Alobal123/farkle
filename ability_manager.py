from __future__ import annotations
from typing import List, Optional
from ability import Ability, RerollAbility, TargetedAbility

class AbilityManager:
    def __init__(self, game):
        self.game = game
        self.abilities: List[Ability] = []
        # Register default abilities
        self.register(RerollAbility())

    def register(self, ability: Ability):
        self.abilities.append(ability)

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
        # Handle state transitions when entering/exiting selection mode
        if ability.selectable:
            if not prev_selecting and ability.selecting:
                # Enter selecting state
                try:
                    self.game.state_manager.enter_selecting_targets()
                except Exception:
                    pass
                try:
                    from game_event import GameEvent, GameEventType
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
                    from game_event import GameEvent, GameEventType
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
            a.collected_targets.append(target_index)
            if len(a.collected_targets) >= a.targets_needed:
                executed = a.execute(self, list(a.collected_targets))
                if executed:
                    a.selecting = False
                    try:
                        self.game.state_manager.exit_selecting_targets()
                    except Exception:
                        pass
                    try:
                        from game_event import GameEvent, GameEventType
                        self.game.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_FINISHED, payload={"ability": a.id}))
                    except Exception:
                        pass
                return executed
            else:
                # Provide UI feedback via message if available
                try:
                    self.game.set_message(f"Select {a.targets_needed - len(a.collected_targets)} more target(s) for {a.name}.")
                except Exception:
                    pass
                return True  # partial progress
        else:
            executed = a.execute(self, target_index)
            if executed:
                a.selecting = False
                try:
                    self.game.state_manager.exit_selecting_targets()
                except Exception:
                    pass
                try:
                    from game_event import GameEvent, GameEventType
                    self.game.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_FINISHED, payload={"ability": a.id, "target_index": target_index}))
                except Exception:
                    pass
            return executed
