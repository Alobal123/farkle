import pygame
from game_event import GameEvent, GameEventType
from typing import List  # Tuple removed after pruning compute_button_states
from settings import (
    WIDTH, HEIGHT, DICE_SIZE, BG_COLOR, BTN_ROLL_COLOR, BTN_LOCK_COLOR_DISABLED, BTN_LOCK_COLOR_ENABLED,
    BTN_BANK_COLOR, TEXT_PRIMARY, TEXT_ACCENT,
    GOAL_BG_MANDATORY, GOAL_BG_MANDATORY_DONE, GOAL_BG_OPTIONAL, GOAL_BG_OPTIONAL_DONE,
    GOAL_BORDER_ACTIVE, GOAL_TEXT, GOAL_PADDING, GOAL_WIDTH, GOAL_LINE_SPACING,
    ROLL_BTN, LOCK_BTN, BANK_BTN, NEXT_BTN, REROLL_BTN
)

class GameRenderer:
    def __init__(self, game):
        self.game = game
        # Shop panel dimensions (enlarged)
        self.SHOP_PANEL_WIDTH = 600
        self.SHOP_PANEL_HEIGHT = 340
        # Help overlay state
        self.help_icon_rect = pygame.Rect(10, self.game.screen.get_height() - 50, 40, 40)
        self.show_help = False
        # Debug toggle for showing active relics (always on for now)
        self.show_relic_debug = True
        # Backwards-compat attributes expected by existing tests. Now also populated by ShopOverlay GameObject draw later in Game.draw.

    # --- debug helpers -------------------------------------------------
    def get_active_relic_debug_lines(self) -> List[str]:
        """Return human-readable lines describing currently active relics.

        Format per relic: Name (+flat bonuses, multipliers).
        Example: "Charm of Fives [+50 SingleValue:5]" or "Glyph of Triples [x1.50 ThreeOfAKind:*]".
        """
        lines: List[str] = []
        rm = getattr(self.game, 'relic_manager', None)
        if not rm:
            return ["Relics: (manager missing)"]
        if not rm.active_relics:
            return ["Relics: (none)"]
        from score_modifiers import FlatRuleBonus, RuleSpecificMultiplier, ScoreMultiplier
        for relic in rm.active_relics:
            parts: List[str] = []
            try:
                for m in relic.modifier_chain.snapshot():
                    if isinstance(m, FlatRuleBonus):
                        parts.append(f"+{m.amount} {m.rule_key}")
                    elif isinstance(m, RuleSpecificMultiplier):
                        # Collapse rule_key tail for readability
                        rk = getattr(m, 'rule_key', '')
                        parts.append(f"x{getattr(m,'mult',1.0):.2f} {rk}")
                    elif isinstance(m, ScoreMultiplier):
                        if getattr(m, 'mult', 1.0) != 1.0:
                            parts.append(f"x{m.mult:.2f} GLOBAL")
            except Exception:
                pass
            suffix = (" [" + ", ".join(parts) + "]") if parts else ""
            lines.append(f"{relic.name}{suffix}")
        return lines


    # Internal helper so click handling can ensure rects exist even before first post-open draw flip

    def handle_click(self, game, pos):
        """Handle a mouse click for dice/goal selection, publishing selection events.

        Signature updated to accept game explicitly for consistency with GameObject pattern.
        """
        g = game
        mx, my = pos
        consumed = False
        # Ability buttons
        if REROLL_BTN.collidepoint(mx, my):
            # Map to ability manager reroll ability
            abm = getattr(g, 'ability_manager', None)
            if abm:
                reroll = abm.get('reroll')
                if reroll and reroll.can_activate(abm):
                    abm.toggle_or_execute('reroll')
                    # Mirror legacy flag for compatibility
                    g.reroll_selecting = bool(reroll.selecting)
                else:
                    g.set_message("No rerolls available.")
            else:
                g.event_listener.publish(GameEvent(GameEventType.REQUEST_REROLL))
            return True
        # Help icon toggle (lowest priority so gameplay UI still works when overlay open)
        if self.help_icon_rect.collidepoint(mx, my):
            self.show_help = not self.show_help
            return True
        # Shop click handling has priority
        if getattr(g, 'relic_manager', None) and g.relic_manager.shop_open:
            # First attempt: delegate to ShopOverlay GameObject if present (authoritative source of rects)
            try:
                from ui_objects import ShopOverlay as _ShopOverlay
                for obj in getattr(g, 'ui_misc', []):
                    if isinstance(obj, _ShopOverlay):
                        if obj.handle_click(g, (mx,my)):
                            return True
            except Exception:
                pass

        # Dice selection
        if g.state_manager.get_state() == g.state_manager.state.ROLLING:
            for d in g.dice:
                if d.rect().collidepoint(mx, my) and (not d.held):
                    # Ability selection check
                    abm = getattr(g, 'ability_manager', None)
                    if abm and abm.is_selecting():
                        sel = abm.selecting_ability()
                        if sel and sel.target_type == 'die':
                            if abm.attempt_target('die', g.dice.index(d)):
                                g.reroll_selecting = False
                                consumed = True
                                break
                    # Normal selection path requires scoring eligibility
                    if d.scoring_eligible:
                        d.toggle_select()
                        g.update_current_selection_score()
                        g.event_listener.publish(
                            GameEvent(
                                GameEventType.DIE_SELECTED if d.selected else GameEventType.DIE_DESELECTED,
                                payload={"index": g.dice.index(d)}
                            )
                        )
                        consumed = True
                        break
        # Goal selection via each goal's cached rect from last draw
        for idx, goal in enumerate(g.level_state.goals):
            rect = getattr(goal, '_last_rect', None)
            if rect and rect.collidepoint(mx, my):
                g.active_goal_index = idx
                consumed = True
                break
        return consumed

    # Button state & selection preview logic migrated to Game / button factories.
    def draw(self):
        g = self.game
        screen = g.screen
        screen.fill(BG_COLOR)
        shop_open = getattr(g, 'relic_manager', None) and g.relic_manager.shop_open
        # When shop open, dim gameplay background
        if g.state_manager.get_state() in (g.state_manager.state.ROLLING, g.state_manager.state.FARKLE, g.state_manager.state.BANKED):
            abm = getattr(g, 'ability_manager', None)
            selecting_reroll = False
            if abm:
                sel = abm.selecting_ability()
                selecting_reroll = bool(sel and sel.id == 'reroll')
            # Draw dynamic objects (currently dice) via unified list
            for obj in getattr(g, 'ui_dynamic', []):
                try:
                    obj.draw(screen)  # type: ignore[attr-defined]
                    # If reroll selecting highlight dice that are not held
                    if selecting_reroll and hasattr(obj, 'held') and hasattr(obj, 'x') and hasattr(obj, 'y') and not getattr(obj, 'held'):
                        overlay = pygame.Surface((getattr(obj, 'size', DICE_SIZE), getattr(obj, 'size', DICE_SIZE)), pygame.SRCALPHA)
                        overlay.fill((60, 220, 140, 90))
                        screen.blit(overlay, (getattr(obj, 'x'), getattr(obj, 'y')))
                except Exception:
                    pass
        # Buttons
        # Button objects render their own enabled state via callbacks; no local state calc needed.
        # Draw buttons via GameObjects
        for btn in getattr(g, 'ui_buttons', []):
            btn.draw_with_game(g, screen)
        if g.state_manager.get_state() in (g.state_manager.state.FARKLE, g.state_manager.state.BANKED):
            pygame.draw.rect(screen, (200, 50, 50), NEXT_BTN, border_radius=10)
            screen.blit(g.font.render("Next Turn", True, (255, 255, 255)), (NEXT_BTN.x + 10, NEXT_BTN.y + 10))
        # Status message
        screen.blit(g.font.render(g.message, True, TEXT_PRIMARY), (80, 60))
        # Score preview
        dice_bottom_y = HEIGHT // 2 - DICE_SIZE // 2 + DICE_SIZE
        score_y = dice_bottom_y + 15
        # New richer selection preview
        # Turn Score now directly displays accumulated turn_score without speculative pending selection addition.
        screen.blit(g.font.render(f"Turn Score: {g.turn_score}", True, TEXT_PRIMARY), (100, score_y))
        raw_sel, selective_sel, final_sel, total_mult = g.selection_preview()
        if raw_sel > 0:
            # Build preview string
            if selective_sel != raw_sel and final_sel != selective_sel and total_mult != 1.0:
                sel_text = f"Selecting: {raw_sel} -> {selective_sel} -> {final_sel}"
            elif selective_sel != raw_sel:
                sel_text = f"Selecting: {raw_sel} -> {selective_sel}"
            elif final_sel != raw_sel and total_mult != 1.0:
                sel_text = f"Selecting: {raw_sel} -> {final_sel}"
            else:
                sel_text = f"Selecting: {raw_sel}"
            screen.blit(g.font.render(sel_text, True, TEXT_ACCENT), (100, score_y + 25))
        # Goals now render themselves
        for goal in g.level_state.goals:
            goal.draw(screen)
        screen.blit(g.font.render(f"Level {g.level_index}", True, (180, 220, 255)), (80, 30))
        # Debug: warn if shop should be open but is not (recent LEVEL_ADVANCE_FINISHED without SHOP_OPENED)
        try:
            recent = getattr(g, '_recent_events', [])[-10:]
            saw_finished = any(e.type == GameEventType.LEVEL_ADVANCE_FINISHED for e in recent)
            saw_shop_open = any(e.type == GameEventType.SHOP_OPENED for e in recent)
            if saw_finished and not saw_shop_open and g.state_manager.get_state().name != 'SHOP':
                warn = g.font.render('DEBUG: Shop expected but not open', True, (255,80,80))
                screen.blit(warn, (80, 5))
        except Exception:
            pass
    # Note: display flip moved to Game.draw after overlay objects render.

# Note: Avoid importing Game for type checking to prevent circular dependency.
