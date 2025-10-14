import pygame
from game_event import GameEvent, GameEventType
from typing import List, Tuple  # Tuple kept for type hints elsewhere
from settings import (
    WIDTH, HEIGHT, DICE_SIZE, BG_COLOR, BTN_ROLL_COLOR, BTN_LOCK_COLOR_DISABLED, BTN_LOCK_COLOR_ENABLED,
    BTN_BANK_COLOR, TEXT_PRIMARY, TEXT_ACCENT,
    GOAL_BG_MANDATORY, GOAL_BG_MANDATORY_DONE, GOAL_BG_OPTIONAL, GOAL_BG_OPTIONAL_DONE,
    GOAL_BORDER_ACTIVE, GOAL_TEXT, GOAL_PADDING, GOAL_WIDTH, GOAL_LINE_SPACING,
    ROLL_BTN, LOCK_BTN, BANK_BTN, NEXT_BTN
)

class GameRenderer:
    def __init__(self, game):
        self.game = game
        self.goal_boxes: List[pygame.Rect] = []
        self.shop_purchase_rect = None
        self.shop_skip_rect = None
        # Shop panel dimensions (enlarged)
        self.SHOP_PANEL_WIDTH = 600
        self.SHOP_PANEL_HEIGHT = 340
        # Help overlay state
        self.help_icon_rect = pygame.Rect(10, self.game.screen.get_height() - 50, 40, 40)
        self.show_help = False
        # Debug toggle for showing active relics (always on for now)
        self.show_relic_debug = True

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

    def _compute_goal_pending_final(self, goal) -> int:
        """Return the projected final (post selective + global) score for this goal's current pending_raw.

        Rebuild a Score from the goal's internal _pending_score parts (if present) and reapply selective
        modifiers (to ensure each part receives flat/mult bonuses) then multiply by all global multipliers.
        Falls back to pending_raw if anything fails.
        """
        pending_raw = getattr(goal, 'pending_raw', 0)
        if pending_raw <= 0:
            return 0
        g = self.game
        orig_score_obj = None
        try:
            orig_score_obj = getattr(goal, '_pending_score', None)
        except Exception:
            orig_score_obj = None
        if orig_score_obj is None:
            return pending_raw
        try:
            # Work on a clone to avoid mutating real pending parts (idempotent preview)
            score_obj = orig_score_obj.clone()
            # Re-run selective modifiers across each part (non-global only). Use same logic as preview.
            from score_modifiers import ScoreMultiplier as _SM
            # Build a lightweight context carrying score_obj
            ctx = type('TmpCtx',(object,),{'score_obj':score_obj, 'pending_raw':pending_raw})()
            # Player selective modifiers
            for m in g.player.modifier_chain.snapshot():
                if isinstance(m, _SM):
                    continue
                try:
                    _ = m.apply(score_obj.total_effective, ctx)  # type: ignore[arg-type]
                except Exception:
                    pass
            # Relic selective modifiers
            relic_manager = getattr(g, 'relic_manager', None)
            if relic_manager is not None:
                for r in relic_manager.active_relics:
                    for m in r.modifier_chain.snapshot():
                        if isinstance(m, _SM):
                            continue
                        try:
                            _ = m.apply(score_obj.total_effective, ctx)  # type: ignore[arg-type]
                        except Exception:
                            pass
            selective_total = score_obj.total_effective
            # Global multipliers
            total_mult = 1.0
            for m in g.player.modifier_chain.snapshot():
                if isinstance(m, _SM):
                    total_mult *= m.mult
            if relic_manager is not None:
                for r in relic_manager.active_relics:
                    for m in r.modifier_chain.snapshot():
                        if isinstance(m, _SM):
                            total_mult *= m.mult
            return int(selective_total * total_mult)
        except Exception:
            return pending_raw

    # Internal helper so click handling can ensure rects exist even before first post-open draw flip

    def handle_click(self, pos):
        """Handle a mouse click for dice/goal selection, publishing selection events."""
        g = self.game
        mx, my = pos
        consumed = False
        # Help icon toggle (lowest priority so gameplay UI still works when overlay open)
        if self.help_icon_rect.collidepoint(mx, my):
            self.show_help = not self.show_help
            return True
        # Shop click handling has priority
        if getattr(g, 'relic_manager', None) and g.relic_manager.shop_open:
            # Multi-offer support: purchase buttons stored as list
            purchase_buttons = getattr(self, 'shop_purchase_rects', [])
            for idx, rect in enumerate(purchase_buttons):
                if rect.collidepoint(mx, my):
                    g.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC, payload={"offer_index": idx}))
                    return True
            if self.shop_skip_rect and self.shop_skip_rect.collidepoint(mx, my):
                g.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP))
                return True
        # Dice selection
        if g.state_manager.get_state() == g.state_manager.state.ROLLING:
            for d in g.dice:
                if d.rect().collidepoint(mx, my) and (not d.held) and d.scoring_eligible:
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
        # Goal selection
        if hasattr(self, 'goal_boxes'):
            for idx, rect in enumerate(self.goal_boxes):
                if rect.collidepoint(mx, my):
                    g.active_goal_index = idx
                    consumed = True
                    break
        return consumed

    def compute_button_states(self) -> Tuple[bool, bool, bool]:
        g = self.game
        current_state = g.state_manager.get_state()
        if current_state == g.state_manager.state.START:
            roll_enabled = True
        else:
            valid_combo = g.selection_is_single_combo() and g.any_scoring_selection()
            roll_enabled = current_state == g.state_manager.state.ROLLING and (g.locked_after_last_roll or valid_combo)
        lock_enabled = g.selection_is_single_combo() and g.any_scoring_selection() and current_state in (g.state_manager.state.START, g.state_manager.state.ROLLING)
        valid_combo = g.selection_is_single_combo() and g.any_scoring_selection()
        bank_enabled = (
            current_state == g.state_manager.state.ROLLING and (
                (g.turn_score > 0 and not any(d.selected for d in g.dice)) or valid_combo
            )
        )
        return roll_enabled, lock_enabled, bank_enabled

    # Removed legacy compute_preview_scores in favor of richer selection preview pipeline.

    # New unified selection preview returning (raw, selective, final, total_mult)
    def get_selection_preview(self) -> Tuple[int,int,int,float]:
        g = self.game
        if not (g.selection_is_single_combo() and g.any_scoring_selection()):
            return (0,0,0,1.0)
        # Raw score for the selection (single combo restriction already ensures atomicity)
        raw, _ = g.calculate_score_from_dice()
        if raw <= 0:
            return (0,0,0,1.0)
        # Determine rule_key
        try:
            rk = g.dice_container.selection_rule_key()
        except Exception:
            rk = None
        # Selective adjusted using game's helper
        selective = g._preview_selective_adjust(rk, raw) if rk else raw
        # Global multipliers (player + relic ScoreMultiplier)
        from score_modifiers import ScoreMultiplier as _SM
        total_mult = 1.0
        try:
            for m in g.player.modifier_chain:
                if isinstance(m, _SM): total_mult *= m.mult
        except Exception:
            pass
        try:
            for r in getattr(g, 'relic_manager', []).active_relics:  # type: ignore[union-attr]
                for m in r.modifier_chain.snapshot():
                    if isinstance(m, _SM): total_mult *= m.mult
        except Exception:
            pass
        final_val = int(selective * total_mult)
        return (raw, selective, final_val, total_mult)

    def draw(self):
        g = self.game
        screen = g.screen
        screen.fill(BG_COLOR)
        shop_open = getattr(g, 'relic_manager', None) and g.relic_manager.shop_open
        # When shop open, dim gameplay background
        if g.state_manager.get_state() in (g.state_manager.state.ROLLING, g.state_manager.state.FARKLE, g.state_manager.state.BANKED):
            for d in g.dice:
                d.draw(screen)
        # Buttons
        def dim(color):
            return tuple(max(0, int(c * 0.45)) for c in color)
        roll_enabled, lock_enabled, bank_enabled = self.compute_button_states()
        # Hard-disable button visuals while shop open
        if shop_open:
            roll_enabled = lock_enabled = bank_enabled = False
        roll_color = BTN_ROLL_COLOR if roll_enabled else dim(BTN_ROLL_COLOR)
        lock_color = BTN_LOCK_COLOR_ENABLED if lock_enabled else dim(BTN_LOCK_COLOR_DISABLED)
        bank_color = BTN_BANK_COLOR if bank_enabled else dim(BTN_BANK_COLOR)
        pygame.draw.rect(screen, roll_color, ROLL_BTN, border_radius=10)
        pygame.draw.rect(screen, lock_color, LOCK_BTN, border_radius=10)
        pygame.draw.rect(screen, bank_color, BANK_BTN, border_radius=10)
        def label_color(enabled: bool) -> Tuple[int,int,int]:
            return (0,0,0) if enabled else (60,60,60)
        screen.blit(g.font.render("ROLL", True, label_color(roll_enabled)), (ROLL_BTN.x + 25, ROLL_BTN.y + 10))
        screen.blit(g.font.render("LOCK", True, label_color(lock_enabled)), (LOCK_BTN.x + 25, LOCK_BTN.y + 10))
        screen.blit(g.font.render("BANK", True, label_color(bank_enabled)), (BANK_BTN.x + 25, BANK_BTN.y + 10))
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
        raw_sel, selective_sel, final_sel, total_mult = self.get_selection_preview()
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
        # Goals layout
        panel_y = 90
        self.goal_boxes = []
        spacing = 16
        total_goals = len(g.level.goals)
        left_x = 80
        right_margin = 40
        available_width = WIDTH - left_x - right_margin - (spacing * (total_goals - 1))
        per_box_width = min(GOAL_WIDTH, int(available_width / total_goals))
        per_box_width = max(140, per_box_width)
        used_width = per_box_width * total_goals + spacing * (total_goals - 1)
        start_x = left_x + (available_width - used_width) // 2 if used_width < available_width else left_x
        max_box_height = 0
        prepared = []
        for i, goal in enumerate(g.level_state.goals):
            base_remaining = goal.get_remaining()
            # Per-goal pending stored directly on goal
            pending_raw = getattr(goal, 'pending_raw', 0)
            player_mult = 1.0
            if hasattr(g, 'player') and hasattr(g.player, 'get_score_multiplier'):
                try:
                    player_mult = float(g.player.get_score_multiplier())  # type: ignore[attr-defined]
                except Exception:
                    player_mult = 1.0
            pending_adjusted = int(pending_raw * player_mult) if pending_raw else 0
            if goal.is_fulfilled():
                remaining_text = "Done"
            else:
                if pending_raw > 0:
                    projected = self._compute_goal_pending_final(goal)
                    # Clamp projection so it doesn't show negative remaining
                    show_after = max(0, base_remaining - projected)
                    remaining_text = f"Rem: {base_remaining} (pending {projected})"
                else:
                    remaining_text = f"Rem: {base_remaining}"
            reward_text = f"Reward: {goal.reward_gold}g" if goal.reward_gold > 0 else ""
            base_desc = g.level.description if i == 0 else ""
            desc = (base_desc + ("\n" + reward_text if base_desc and reward_text else reward_text)).strip()
            lines_out = goal.build_lines(g.small_font, per_box_width, remaining_text, desc, GOAL_PADDING, GOAL_LINE_SPACING)
            box_height = goal.compute_box_height(g.small_font, lines_out, GOAL_PADDING, GOAL_LINE_SPACING)
            prepared.append((goal, lines_out, box_height))
            if box_height > max_box_height:
                max_box_height = box_height
        x = start_x
        for i, (goal, lines_out, box_height) in enumerate(prepared):
            box_rect = pygame.Rect(x, panel_y, per_box_width, max_box_height)
            self.goal_boxes.append(box_rect)
            if goal.mandatory:
                bg = GOAL_BG_MANDATORY_DONE if goal.is_fulfilled() else GOAL_BG_MANDATORY
            else:
                bg = GOAL_BG_OPTIONAL_DONE if goal.is_fulfilled() else GOAL_BG_OPTIONAL
            pygame.draw.rect(screen, bg, box_rect, border_radius=10)
            if i == g.active_goal_index:
                pygame.draw.rect(screen, GOAL_BORDER_ACTIVE, box_rect, width=3, border_radius=10)
            goal.draw_into(screen, box_rect, g.small_font, lines_out, GOAL_PADDING, GOAL_LINE_SPACING, GOAL_TEXT)
            x += per_box_width + spacing
        screen.blit(g.font.render(f"Level {g.level_index}", True, (180, 220, 255)), (80, 30))
        # Player HUD box (top-right)
        hud_padding = 10
        # Combined multiplier (player * relics)
        base_mult = 1.0
        try:
            base_mult = float(g.player.get_score_multiplier())
        except Exception:
            base_mult = 1.0
        relic_mult_product = 1.0
        if getattr(g, 'relic_manager', None):
            for r in g.relic_manager.active_relics:
                try:
                    relic_mult_product *= r.get_effective_multiplier()
                except Exception:
                    pass
        mult = base_mult * relic_mult_product
        hud_lines = [f"Turns: {g.level_state.turns_left}", f"Gold: {g.player.gold}"]
        if relic_mult_product != 1.0:
            hud_lines.append(f"Mult: x{base_mult:.2f} * x{relic_mult_product:.2f} = x{mult:.2f}")
        else:
            hud_lines.append(f"Mult: x{mult:.2f}")
        # Determine widest line
        line_surfs = [g.small_font.render(t, True, (250,250,250)) for t in hud_lines]
        width_needed = max(s.get_width() for s in line_surfs) + hud_padding * 2
        height_needed = sum(s.get_height() for s in line_surfs) + hud_padding * 2 + 6
        hud_rect = pygame.Rect(WIDTH - width_needed - 20, 20, width_needed, height_needed)
        pygame.draw.rect(screen, (40, 55, 70), hud_rect, border_radius=8)
        pygame.draw.rect(screen, (90, 140, 180), hud_rect, width=2, border_radius=8)
        y = hud_rect.y + hud_padding
        for s in line_surfs:
            screen.blit(s, (hud_rect.x + hud_padding, y))
            y += s.get_height() + 2
        # Active relic debug list (below HUD, right side)
        if self.show_relic_debug and not shop_open:
            try:
                relic_lines = self.get_active_relic_debug_lines()
            except Exception:
                relic_lines = ["Relics: (error)"]
            # Render in small font, top-right under HUD box
            rpad = 6
            r_line_surfs = [g.small_font.render(ln, True, (220,220,230)) for ln in relic_lines]
            r_width = max(s.get_width() for s in r_line_surfs) + rpad*2
            r_height = sum(s.get_height() for s in r_line_surfs) + rpad*2 + 4
            # Position just under hud_rect with slight gap
            relic_rect = pygame.Rect(hud_rect.right - r_width, hud_rect.bottom + 8, r_width, r_height)
            pygame.draw.rect(screen, (35,50,62), relic_rect, border_radius=6)
            pygame.draw.rect(screen, (80,120,155), relic_rect, width=1, border_radius=6)
            ry = relic_rect.y + rpad
            for rs in r_line_surfs:
                screen.blit(rs, (relic_rect.x + rpad, ry))
                ry += rs.get_height() + 2
        # Draw shop overlay (before single flip) so no flicker from double buffering
        if shop_open:
            self._draw_shop_overlay(screen)
        # Draw help icon always (above dim/shopped content, below overlay panel if open)
        self._draw_help_icon(screen)
        if self.show_help and not shop_open:
            self._draw_rules_overlay(screen)
        pygame.display.flip()

    def _draw_shop_overlay(self, screen):
        g = self.game
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        screen.blit(overlay, (0,0))
        # Offer panel
        panel_w, panel_h = self.SHOP_PANEL_WIDTH, self.SHOP_PANEL_HEIGHT
        panel_rect = pygame.Rect((WIDTH - panel_w)//2, (HEIGHT - panel_h)//2, panel_w, panel_h)
        pygame.draw.rect(screen, (50,70,95), panel_rect, border_radius=12)
        pygame.draw.rect(screen, (120,170,210), panel_rect, width=2, border_radius=12)
        font = g.font
        title_surf = font.render("Shop", True, (250,250,250))
        screen.blit(title_surf, (panel_rect.x + 20, panel_rect.y + 16))
        gold_surf = font.render(f"Your Gold: {g.player.gold}", True, (230,230,230))
        screen.blit(gold_surf, (panel_rect.x + 20, panel_rect.y + 16 + title_surf.get_height() + 6))
        offers = getattr(g.relic_manager, 'offers', [])
        # Layout offers in columns (up to 3)
        offer_area_top = panel_rect.y + 90
        offer_width = (panel_rect.width - 80) // 3
        offer_height = panel_rect.height - 150
        self.shop_purchase_rects = []
        for idx, offer in enumerate(offers):
            col_x = panel_rect.x + 20 + idx * (offer_width + 20)
            box_rect = pygame.Rect(col_x, offer_area_top, offer_width, offer_height)
            pygame.draw.rect(screen, (65,90,120), box_rect, border_radius=8)
            pygame.draw.rect(screen, (120,170,210), box_rect, width=2, border_radius=8)
            y = box_rect.y + 12
            name_surf = font.render(offer.relic.name, True, (255,255,255))
            screen.blit(name_surf, (box_rect.x + 10, y))
            y += name_surf.get_height() + 6
            mult = offer.relic.get_effective_multiplier()
            if mult != 1.0:
                msurf = g.small_font.render(f"Multiplier: x{mult:.2f}", True, (230,230,230))
                screen.blit(msurf, (box_rect.x + 10, y)); y += msurf.get_height() + 4
            # Flat bonuses enumeration
            from score_modifiers import FlatRuleBonus
            for m in offer.relic.modifier_chain.snapshot():
                if isinstance(m, FlatRuleBonus):
                    fsurf = g.small_font.render(f"+{m.amount} {m.rule_key}", True, (255,200,140))
                    screen.blit(fsurf, (box_rect.x + 10, y)); y += fsurf.get_height() + 2
            csurf = g.small_font.render(f"Cost: {offer.cost}g", True, (210,210,210))
            screen.blit(csurf, (box_rect.x + 10, y)); y += csurf.get_height() + 8
            # Purchase button
            btn_h = 32
            btn_rect = pygame.Rect(box_rect.x + 10, box_rect.bottom - btn_h - 10, box_rect.width - 20, btn_h)
            can_afford = g.player.gold >= offer.cost
            pygame.draw.rect(screen, (80,200,110) if can_afford else (60,90,70), btn_rect, border_radius=6)
            ptxt = g.small_font.render("Purchase", True, (0,0,0) if can_afford else (120,120,120))
            screen.blit(ptxt, (btn_rect.centerx - ptxt.get_width()//2, btn_rect.centery - ptxt.get_height()//2))
            self.shop_purchase_rects.append(btn_rect)
        # Legacy single rect reference for tests expecting shop_purchase_rect
        if self.shop_purchase_rects:
            self.shop_purchase_rect = self.shop_purchase_rects[0]
        # Skip button across bottom
        skip_rect = pygame.Rect(panel_rect.centerx - 80, panel_rect.bottom - 50, 160, 40)
        pygame.draw.rect(screen, (180,80,60), skip_rect, border_radius=8)
        stxt = font.render("Skip", True, (0,0,0))
        screen.blit(stxt, (skip_rect.centerx - stxt.get_width()//2, skip_rect.centery - stxt.get_height()//2))
        self.shop_skip_rect = skip_rect

    def _draw_help_icon(self, screen):
        # Simple circle with '?' inside bottom-left
        rect = self.help_icon_rect
        pygame.draw.circle(screen, (60,90,120), rect.center, rect.width//2)
        pygame.draw.circle(screen, (140,190,230), rect.center, rect.width//2, width=2)
        qsurf = self.game.font.render('?', True, (255,255,255))
        screen.blit(qsurf, (rect.centerx - qsurf.get_width()//2, rect.centery - qsurf.get_height()//2))

    def _draw_rules_overlay(self, screen):
        # Semi-transparent background
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        screen.blit(overlay, (0,0))
        # Panel
        panel_w, panel_h = 660, 440
        panel_rect = pygame.Rect(20, HEIGHT - panel_h - 40, panel_w, panel_h)
        pygame.draw.rect(screen, (40,55,70), panel_rect, border_radius=10)
        pygame.draw.rect(screen, (90,140,180), panel_rect, width=2, border_radius=10)
        title = self.game.font.render("Scoring Rules", True, (240,240,240))
        screen.blit(title, (panel_rect.x + 16, panel_rect.y + 16))
        # Build structured listing so straights are guaranteed visible and multi-of-a-kind grouped
        by_key = {r.rule_key: r for r in self.game.rules.rules}
        lines: List[str] = []
        # Straights first
        for key, label in [( 'Straight6', 'Straight 1-6'), ('Straight1to5','Straight 1-5'), ('Straight2to6','Straight 2-6')]:
            r = by_key.get(key)
            if r:
                pts = getattr(r, 'points', None)
                if pts:
                    lines.append(f"{label}: {pts}")
        # Singles
        for sv in ('1','5'):
            r = by_key.get(f'SingleValue:{sv}')
            if r:
                pts = getattr(r, 'points', None)
                if pts:
                    lines.append(f"Single {sv}s: {pts} each")
        # Of-a-kind (value ascending)
        for v in range(1,7):
            three = by_key.get(f'ThreeOfAKind:{v}')
            if not three:
                continue
            base = getattr(three, 'points', None)
            if not base:
                continue
            four = by_key.get(f'FourOfAKind:{v}')
            five = by_key.get(f'FiveOfAKind:{v}')
            six = by_key.get(f'SixOfAKind:{v}')
            # Derive scaled values from base three-kind config
            line_parts = [f"{v}: 3-kind {base}"]
            if four:
                line_parts.append(f"4-kind {base*2}")
            if five:
                line_parts.append(f"5-kind {base*3}")
            if six:
                line_parts.append(f"6-kind {base*4}")
            lines.append("Of-a-Kind " + ", ".join(line_parts))
        # Render in two columns if overflow
        small_font = self.game.small_font if hasattr(self.game, 'small_font') else self.game.font
        line_height = small_font.get_height() + 4
        max_rows = 14
        columns = 1 if len(lines) <= max_rows else 2
        col_width = (panel_w - 40) // columns
        start_y = panel_rect.y + 60
        for idx, ln in enumerate(lines):
            col = idx // max_rows if columns > 1 else 0
            row = idx % max_rows if columns > 1 else idx
            if start_y + (row+1)*line_height > panel_rect.bottom - 40:
                # Stop if no space (edge case if too many lines even for two columns)
                break
            x = panel_rect.x + 20 + col * col_width
            y = start_y + row * line_height
            surf = small_font.render(ln, True, (230,230,235))
            screen.blit(surf, (x, y))
        hint = small_font.render("Click ? to close", True, (190,200,210))
        screen.blit(hint, (panel_rect.x + 20, panel_rect.bottom - 28))

# Note: Avoid importing Game for type checking to prevent circular dependency.
