from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Any, Sequence
from farkle.core.game_event import GameEvent, GameEventType
from farkle.core.game_object import GameObject

class AbilityContext(Protocol):
    game: Any

@dataclass
class Ability(GameObject):
    id: str
    name: str
    charges_per_level: int = 0
    selectable: bool = False  # if True requires target selection
    target_type: str | None = None  # e.g. 'die'
    description: str = ""
    # Internal runtime state
    charges_used: int = 0
    selecting: bool = False

    def __post_init__(self):
        # Preserve ability's string id while initializing GameObject which defines its own numeric id
        _ability_id = self.id
        GameObject.__init__(self, self.name)
        # Store numeric GameObject id separately
        self.object_id = self.id  # type: ignore[attr-defined]
        # Restore ability string id
        self.id = _ability_id
        # Abilities are logic-only; remain active so they receive events once subscribed.
        # Subscription is coordinated by AbilityManager after event_listener exists.
        # Debug logging removed after stabilization.

    # --- GameObject required draw override ---
    def draw(self, surface):  # type: ignore[override]
        # Abilities do not render directly.
        return None

    def available(self) -> int:
        return max(0, self.charges_per_level - self.charges_used)

    def can_activate(self, ctx: AbilityContext) -> bool:
        return self.available() > 0

    def begin(self, ctx: AbilityContext) -> bool:
        if not self.can_activate(ctx):
            return False
        if self.selectable:
            self.selecting = not self.selecting  # toggle
            # If entering selecting mode, clear any prior collected targets (for multi-target abilities)
            if self.selecting and hasattr(self, 'collected_targets'):
                getattr(self, 'collected_targets').clear()
            return self.selecting
        # Immediate execution ability without target
        return self.execute(ctx)

    def execute(self, ctx: AbilityContext, target: Any | None = None) -> bool:  # override
        return False

    def consume(self):
        self.charges_used += 1
        if self.charges_used > self.charges_per_level:
            self.charges_used = self.charges_per_level

    def reset_level(self):
        self.charges_used = 0
        self.selecting = False

    # --- Event handling ---
    def on_event(self, event: GameEvent):  # type: ignore[override]
        # Charge modifications
        if event.type == GameEventType.ABILITY_CHARGES_ADDED:
            ability_id = event.get('ability_id')
            if ability_id != self.id:
                return
            try:
                delta = int(event.get('delta', 0) or 0)
            except Exception:
                return
            if delta == 0:
                return
            try:
                if delta > 0:
                    self.charges_per_level += delta
                else:
                    new_cap = self.charges_per_level + delta
                    if new_cap < self.charges_used:
                        new_cap = self.charges_used
                    self.charges_per_level = max(0, new_cap)
            except Exception:
                return
            return
        # Target count modifications (only for TargetedAbility instances)
        if event.type == GameEventType.ABILITY_TARGETS_ADDED and isinstance(self, TargetedAbility):
            ability_id = event.get('ability_id')
            if ability_id != self.id:
                return
            try:
                delta = int(event.get('delta', 0) or 0)
            except Exception:
                return
            if delta == 0:
                return
            try:
                new_needed = getattr(self, 'targets_needed', 1) + delta
                if new_needed < 1:
                    new_needed = 1
                self.targets_needed = new_needed
            except Exception:
                pass

@dataclass
class TargetedAbility(Ability):
    selectable: bool = True
    # Multi-target support: number of targets required to trigger execution. 1 = existing behavior.
    targets_needed: int = 1
    collected_targets: list[int] = field(default_factory=list)
    # Indicates execution already occurred during selection (auto-execute single target path)
    executed_once: bool = False

    def execute(self, ctx: AbilityContext, target: Any | Sequence[int] | None = None) -> bool:  # still abstract
        raise NotImplementedError

class RerollAbility(TargetedAbility):
    def __init__(self, charges_per_level: int = 1):
        super().__init__(id="reroll", name="Reroll", charges_per_level=charges_per_level, selectable=True, target_type='die', description="Reroll one unheld die.")

    def can_activate(self, ctx: AbilityContext) -> bool:
        # Restrict usage before the first roll of a turn (PRE_ROLL state)
        state_name = ctx.game.state_manager.get_state().name
        if state_name == "PRE_ROLL":
            return False
        return super().can_activate(ctx) and state_name in ("ROLLING","FARKLE")

    def execute(self, ctx: AbilityContext, target: Any | Sequence[int] | None = None) -> bool:
        if target is None:
            return False
        # Support multi-target (sequence) by iterating; stop on first failure.
        if isinstance(target, Sequence) and not isinstance(target, (str, bytes)):
            success_any = False
            for t in target:
                if not self._reroll_single(ctx, t):
                    return success_any  # partial success allowed
                success_any = True
            return success_any
        try:
            idx = int(target)  # type: ignore[arg-type]
        except Exception:
            return False
        return self._reroll_single(ctx, idx)

    def _reroll_single(self, ctx: AbilityContext, die_index: int) -> bool:
        game = ctx.game
        if die_index < 0 or die_index >= len(game.dice):
            return False
        d = game.dice[die_index]
        if d.held:
            game.set_message("Cannot reroll held die."); return False
        import random as _r
        old = d.value
        d.value = _r.randint(1,6)
        d.selected = False
        d.scoring_eligible = False
        self.consume()
        try:
            game.event_listener.publish(GameEvent(GameEventType.DIE_ROLLED, payload={"index": die_index, "old": old, "new": d.value, "ability": self.id}))
            game.event_listener.publish(GameEvent(GameEventType.REROLL, payload={"remaining": self.available(), "ability": self.id}))
            game.event_listener.publish(GameEvent(GameEventType.ABILITY_EXECUTED, payload={"ability": self.id, "target_index": die_index}))
        except Exception:
            pass
        game.mark_scoring_dice()
        # Evaluate underlying play state (handles selecting targets transient) and farkle condition
        underlying_state = getattr(game.state_manager.effective_play_state(), 'name', None)
        visible_state = getattr(game.state_manager.get_state(), 'name', None)
        is_farkle_now = game.check_farkle()
        if underlying_state == 'FARKLE':
            if not is_farkle_now:
                try:
                    game.state_manager.rescue_farkle_to_rolling()
                except Exception:
                    game.state_manager.transition_to_rolling()
                game.set_message("Farkle rescued by reroll! Continue.")
            else:
                game.set_message("Reroll produced no scoring dice. Farkle persists.")
                # Ensure visible state reflects FARKLE (selection ended by ability_manager after execute)
                if visible_state == 'SELECTING_TARGETS':
                    try:
                        game.state_manager.transition_to_farkle()
                    except Exception:
                        pass
                if self.available() == 0:
                    try:
                        game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason":"farkle"}))
                    except Exception:
                        pass
        elif underlying_state == 'ROLLING' and is_farkle_now:
            if visible_state == 'SELECTING_TARGETS':
                # Transition out of selecting and into FARKLE immediately
                try:
                    game.state_manager.exit_selecting_targets()
                except Exception:
                    pass
                try:
                    game.state_manager.transition_to_farkle()
                except Exception:
                    pass
            else:
                try:
                    game.state_manager.transition_to_farkle()
                except Exception:
                    pass
            game.set_message("Farkle! No scoring dice after reroll.")
            if self.available() == 0:
                try:
                    game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason":"farkle"}))
                except Exception:
                    pass
        else:
            game.set_message("Die rerolled.")
        # Defer selecting state exit until finalize_selection so tests calling finalize() still pass
        return True
