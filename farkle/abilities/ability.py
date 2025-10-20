from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Callable, Any, Sequence
from farkle.core.game_event import GameEvent, GameEventType

class AbilityContext(Protocol):
    game: Any

@dataclass
class Ability:
    id: str
    name: str
    charges_per_level: int = 0
    selectable: bool = False  # if True requires target selection
    target_type: str | None = None  # e.g. 'die'
    description: str = ""
    # Internal runtime state
    charges_used: int = 0
    selecting: bool = False

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

@dataclass
class TargetedAbility(Ability):
    selectable: bool = True
    # Multi-target support: number of targets required to trigger execution. 1 = existing behavior.
    targets_needed: int = 1
    collected_targets: list[int] = field(default_factory=list)

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
        # Use effective_play_state to detect underlying FARKLE during targeting
        if getattr(game.state_manager.effective_play_state(), 'name', None) == 'FARKLE':
            if not game.check_farkle():
                try:
                    game.state_manager.rescue_farkle_to_rolling()
                except Exception:
                    game.state_manager.transition_to_rolling()
                game.set_message("Farkle rescued by reroll! Continue.")
                self.selecting = False
            else:
                game.set_message("Reroll produced no scoring dice. Farkle persists.")
                if self.available() == 0:
                    try:
                        game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason":"farkle"}))
                    except Exception:
                        pass
        else:
            game.set_message("Die rerolled.")
        self.selecting = False
        return True
