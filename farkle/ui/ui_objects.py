from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Callable, Optional, Any
from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import (
    BTN_ROLL_COLOR, BTN_BANK_COLOR,
    ROLL_BTN, BANK_BTN, NEXT_BTN, REROLL_BTN
)

Color = tuple[int,int,int]

@dataclass
class UIButton(GameObject):
    rect: pygame.Rect
    label: str
    base_color: Color
    disabled_color: Color
    event_type: Optional[GameEventType] = None
    # dynamic enable function: (game) -> bool
    is_enabled_fn: Callable[[Any], bool] = lambda g: True
    # optional dynamic label fn
    label_fn: Optional[Callable[[Any], str]] = None
    border_radius: int = 10

    def __init__(self, name: str, rect: pygame.Rect, label: str, base_color: Color, disabled_color: Color, event_type: Optional[GameEventType], is_enabled_fn: Callable[[Any], bool], label_fn: Optional[Callable[[Any], str]] = None):
        super().__init__(name)
        self.sprite = None  # populated by UIButtonSprite
        self.rect = rect
        self.label = label
        self.base_color = base_color
        self.disabled_color = disabled_color
        self.event_type = event_type
        self.is_enabled_fn = is_enabled_fn
        self.label_fn = label_fn
        # Buttons visible in core interactive states; reroll shares dice visibility.
        from farkle.core.game_state_enum import GameState
        if name == 'next':
            # Next button visible during any FARKLE (even if reroll rescue is still available).
            # BANKED auto-advances implicitly; manual next not needed.
            self.visible_states = {GameState.FARKLE}
            self.interactable_states = {GameState.FARKLE}
        elif name == 'reroll':
            self.visible_states = {GameState.ROLLING, GameState.FARKLE, GameState.SELECTING_TARGETS}
            self.interactable_states = {GameState.ROLLING, GameState.FARKLE, GameState.SELECTING_TARGETS}
        else:
            # roll & bank buttons hidden in SHOP and FARKLE
            self.visible_states = {GameState.PRE_ROLL, GameState.ROLLING, GameState.SELECTING_TARGETS, GameState.BANKED}
            self.interactable_states = {GameState.PRE_ROLL, GameState.ROLLING, GameState.SELECTING_TARGETS, GameState.BANKED}

    def draw(self, surface: pygame.Surface) -> None:  # satisfy abstract base; sprite handles visual
        return

    def handle_click(self, game, pos) -> bool:  # pass game explicitly
        # Ignore if not visible in current state (lets other buttons process)
        st = game.state_manager.get_state()
        if hasattr(self, 'visible_states') and st not in getattr(self, 'visible_states', set()):
            return False
        if not self.rect.collidepoint(*pos):
            return False
        # If disabled, do not consume so underlying (stacked) button can still act
        if not self.is_enabled_fn(game):
            return False
        if self.name == 'reroll':
            game.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL if self.event_type is None else self.event_type))
            return True
        if self.event_type:
            game.event_listener.publish(GameEvent(self.event_type))
        return True

# Factory to build default buttons list (excluding dynamic ones like shop for now)
def build_core_buttons(game):
    def roll_enabled(g):
        st = g.state_manager.get_state()
        if st == g.state_manager.state.PRE_ROLL:
            return True
        if st == g.state_manager.state.ROLLING:
            valid_combo = g.selection_is_single_combo() and g.any_scoring_selection()
            return g.locked_after_last_roll or valid_combo
        return False
    def bank_enabled(g):
        st = g.state_manager.get_state()
        if st != g.state_manager.state.ROLLING:
            return False
        valid_combo = g.selection_is_single_combo() and g.any_scoring_selection()
        return (g.turn_score > 0 and not any(d.selected for d in g.dice)) or valid_combo
    def reroll_enabled(g):
        abm = getattr(g,'ability_manager',None)
        if not abm: return False
        a = abm.get('reroll')
        return bool(a and a.can_activate(abm))
    def reroll_label(g):
        abm = getattr(g,'ability_manager',None)
        sel = abm.selecting_ability() if abm else None
        reroll = abm.get('reroll') if abm else None
        remaining = reroll.available() if reroll else 0
        star = '*' if (sel and sel.id=='reroll') else ''
        return f"REROLL{star} ({remaining})"
    def next_enabled(g):
        # Always enabled while in a FARKLE state to allow player to forfeit rescue.
        return g.state_manager.get_state() == g.state_manager.state.FARKLE
    def next_label(g):
        # Dynamic label clarifies when a rescue is being skipped.
        abm = getattr(g,'ability_manager',None)
        reroll = abm.get('reroll') if abm else None
        if reroll and reroll.available() > 0:
            return "Skip Rescue (Next Turn)"
        return "Next Turn (Farkle)"
    buttons = [
        UIButton('reroll', REROLL_BTN, 'REROLL', (120,160,200), (120,160,200), None, reroll_enabled, reroll_label),
        UIButton('roll', ROLL_BTN, 'ROLL', BTN_ROLL_COLOR, BTN_ROLL_COLOR, GameEventType.REQUEST_ROLL, roll_enabled),
        UIButton('bank', BANK_BTN, 'BANK', BTN_BANK_COLOR, BTN_BANK_COLOR, GameEventType.REQUEST_BANK, bank_enabled),
    UIButton('next', NEXT_BTN, 'Next Turn', (200,50,50), (200,50,50), GameEventType.REQUEST_NEXT_TURN, next_enabled, next_label),
    ]
    return buttons


class HelpIcon(GameObject):
    """Clickable help icon moved out of renderer.

    Responsibilities:
    - Draw circular '?' icon at fixed bottom-left location.
    - Toggle game.show_help flag on click.
    - High z-order but below full-screen overlays.
    """
    def __init__(self, x: int, y: int, size: int = 40):
        super().__init__(name="HelpIcon")
        import pygame
        self.rect = pygame.Rect(x, y, size, size)
        from farkle.core.game_state_enum import GameState
        self.visible_states = {GameState.PRE_ROLL, GameState.ROLLING, GameState.FARKLE, GameState.SELECTING_TARGETS, GameState.BANKED}
        self.interactable_states = self.visible_states

    def draw(self, surface):  # type: ignore[override]
        return  # sprite handles visual

    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        mx,my = pos
        if self.rect.collidepoint(mx,my):
            setattr(game, 'show_help', not getattr(game, 'show_help', False))
            return True
        return False

class RelicPanel(GameObject):
    """Non-interactive panel listing active relics (debug-style)."""
    def __init__(self):
        super().__init__(name="RelicPanel")
        self._last_rect = None
        from farkle.core.game_state_enum import GameState
        # Hide during shop and targeting to reduce clutter.
        self.visible_states = {GameState.PRE_ROLL, GameState.ROLLING, GameState.FARKLE, GameState.BANKED}
        # Non-interactive
        self.interactable_states = set()

    def draw(self, surface):  # type: ignore[override]
        return  # sprite handles visual
    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        # Non-interactive; return False so event propagates.
        return False


class RulesOverlay(GameObject):
    """Help / rules panel shown when game.show_help True."""
    def __init__(self):
        super().__init__(name="RulesOverlay")
        from farkle.core.game_state_enum import GameState
        # Can be shown over any non-shop state; predicate drives actual toggle.
        self.visible_states = {GameState.PRE_ROLL, GameState.ROLLING, GameState.FARKLE, GameState.SELECTING_TARGETS, GameState.BANKED}
        self.visible_predicate = lambda g: getattr(g, 'show_help', False)
        self.interactable_states = self.visible_states
        self.interactable_predicate = lambda g: getattr(g, 'show_help', False)

    def draw(self, surface):  # type: ignore[override]
        return  # sprite handles visual
    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        # Overlay currently closes via HelpIcon; ignore clicks.
        return False

