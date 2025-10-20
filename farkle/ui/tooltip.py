"""Hover tooltip resolution utilities.

resolve_hover(game, pos) inspects UI elements at the given position and
returns a dict: {"title": str, "lines": list[str]} or None if nothing
descriptive found.

This centralizes tooltip content so inline UI text can stay minimal.
"""
from __future__ import annotations
from typing import Optional, List, Dict
import pygame

def friendly_rule_label(rule_key: str) -> str:
    """Return a human-readable label for a scoring rule key.

    Examples:
    - SingleValue:1 -> "Single 1"
    - ThreeOfAKind:2 -> "Three 2s"
    - FourOfAKind:5 -> "Four 5s"
    - FiveOfAKind:3 -> "Five 3s"
    - SixOfAKind:6 -> "Six 6s"
    - Straight6 -> "Straight 1-6"
    - Straight1to5 -> "Straight 1-5"
    - Straight2to6 -> "Straight 2-6"
    Fallback: return rule_key unchanged.
    """
    if not rule_key:
        return rule_key
    if rule_key.startswith("SingleValue:"):
        v = rule_key.split(":",1)[1]
        return f"Single {v}"
    for prefix, word in [
        ("ThreeOfAKind:", "Three"),
        ("FourOfAKind:", "Four"),
        ("FiveOfAKind:", "Five"),
        ("SixOfAKind:", "Six"),
    ]:
        if rule_key.startswith(prefix):
            v = rule_key.split(":",1)[1]
            return f"{word} {v}s"
    if rule_key == "Straight6":
        return "Straight 1-6"
    if rule_key == "Straight1to5":
        return "Straight 1-5"
    if rule_key == "Straight2to6":
        return "Straight 2-6"
    return rule_key

def _wrap(font: pygame.font.Font, text: str, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def resolve_hover(game, pos: tuple[int,int]) -> Optional[Dict]:
    mx, my = pos
    # If the shop is open, treat its panel/buttons as exclusive hover targets before any other UI.
    try:
        if getattr(game.relic_manager, 'shop_open', False):
            # Find ShopOverlay object
            shop_obj = None
            for obj in getattr(game, 'ui_misc', []):
                if getattr(obj, 'name', None) == 'ShopOverlay':
                    shop_obj = obj; break
            if shop_obj and getattr(shop_obj, 'panel_rect', None) and shop_obj.panel_rect.collidepoint(mx,my):
                # Purchase buttons
                offers = getattr(game.relic_manager, 'offers', [])
                purchase_rects = getattr(shop_obj, 'purchase_rects', [])
                for idx, rect in enumerate(purchase_rects):
                    if rect.collidepoint(mx,my) and idx < len(offers):
                        offer = offers[idx]
                        relic = offer.relic
                        lines: List[str] = []
                        lines.append(f"Cost: {offer.cost} gold")
                        # List modifiers (flat bonuses, multipliers)
                        try:
                            from farkle.scoring.score_modifiers import FlatRuleBonus, RuleSpecificMultiplier
                            for m in relic.modifier_chain.snapshot():
                                if isinstance(m, FlatRuleBonus):
                                    lines.append(f"+{m.amount} {m.rule_key} points")
                                elif isinstance(m, RuleSpecificMultiplier):
                                    lines.append(f"x{getattr(m,'mult',1.0):.2f} {getattr(m,'rule_key','')} parts")
                        except Exception:
                            pass
                        return {"title": relic.name, "lines": lines, "target": rect.copy(), "id": f"shop_offer_{idx}"}
                # Skip button
                skip_rect = getattr(shop_obj, 'skip_rect', None)
                if skip_rect and skip_rect.collidepoint(mx,my):
                    return {"title": "Skip Shop", "lines": ["Close the shop without purchasing.", "Begin first turn of new level."], "target": skip_rect.copy(), "id": "shop_skip"}
                # Panel background (generic help)
                if getattr(shop_obj, 'panel_rect', None) and shop_obj.panel_rect.collidepoint(mx,my):
                    return {"title": "Relic Shop", "lines": ["Hover relic to see details.", "Click Purchase if you have enough gold.", "Or Skip to start playing."], "target": shop_obj.panel_rect.copy(), "id": "shop_panel"}
    except Exception:
        pass
    # Goals
    try:
        goals = list(getattr(game.level_state, 'goals', []))
        for goal in goals:
            rect = getattr(goal, '_last_rect', None)
            if rect and rect.collidepoint(mx,my):
                applied = goal.target_score - goal.remaining
                pending_raw = getattr(goal, 'pending_raw', 0)
                projected = 0
                if pending_raw > 0 and not goal.is_fulfilled():
                    try:
                        projected = goal.projected_pending()
                    except Exception:
                        projected = pending_raw
                # Selection preview (only if this goal active)
                preview_add = 0
                try:
                    if game.active_goal_index == game.level_state.goals.index(goal):
                        prev = game.selection_preview()
                        if prev and prev[0] > 0:
                            preview_add = int(prev[2])
                except Exception:
                    preview_add = 0
                status_parts = [f"Applied: {applied}/{goal.target_score}"]
                if projected:
                    status_parts.append(f"Pending: +{projected}")
                if preview_add:
                    status_parts.append(f"Preview: +{preview_add}")
                if goal.reward_gold and goal.is_fulfilled() and not goal.reward_claimed:
                    status_parts.append(f"Reward ready: {goal.reward_gold}g")
                rem_line = f"Remaining: {goal.remaining}" if not goal.is_fulfilled() else "Fulfilled" 
                lines: List[str] = [rem_line] + status_parts
                if getattr(game.level, 'description', '') and game.level_state.goals.index(goal) == 0:
                    lines.append(game.level.description)
                tag = "Mandatory" if goal.mandatory else "Optional"
                idx_goal = goals.index(goal)
                return {"title": f"{goal.name} ({tag})", "lines": lines, "target": rect.copy(), "id": f"goal_{idx_goal}"}
    except Exception:
        pass
    # 3. Dice (only during rolling/selecting states). Do NOT early-return None if die not eligible; allow buttons below to resolve.
    try:
        if game.state_manager.get_state() in (game.state_manager.state.ROLLING, game.state_manager.state.FARKLE, game.state_manager.state.SELECTING_TARGETS):
            for d in game.dice:
                if d.rect().collidepoint(mx,my):
                    if not (d.selected or d.held):
                        break  # uninteractable die under cursor; continue to other UI elements
                    lines: List[str] = []
                    if d.held and getattr(d, 'combo_rule_key', None) and getattr(d, 'combo_points', None):
                        fr = friendly_rule_label(getattr(d,'combo_rule_key'))
                        lines.append(f"Locked: {fr} = {d.combo_points}")
                    elif d.selected and game.selection_is_single_combo() and game.any_scoring_selection():
                        try:
                            raw, _, = game.calculate_score_from_dice()
                            rk = game.dice_container.selection_rule_key()
                            if rk and raw > 0:
                                fr = friendly_rule_label(rk)
                                lines.append(f"Selecting: {fr} = {raw}")
                        except Exception:
                            pass
                    return {"title": f"Die {d.value}", "lines": lines or ["Die"], "target": d.rect().copy(), "id": f"die_{game.dice.index(d)}"}
    except Exception:
        pass
    # 4. Buttons
    try:
        for btn in getattr(game, 'ui_buttons', []):
            if btn.rect.collidepoint(mx,my):
                desc_map = {
                    'roll': ["Roll all non-held dice.", "Automatically enters rolling state."],
                    'bank': ["Bank locked combos to goals.", "Ends turn and applies pending points."],
                    'reroll': ["Select a subset of non-held dice to reroll.", "Right-click to auto-lock combos separately."],
                    'next': ["Advance to next turn."]
                }
                lines = desc_map.get(btn.name, ["Button action."])
                # Provide element-specific delay override for buttons
                # Import button delay from new consolidated ui.settings (fallback to 900ms)
                delay_override = 900
                try:
                    from farkle.ui.settings import TOOLTIP_BUTTON_DELAY_MS as _BTN_DELAY
                    delay_override = int(_BTN_DELAY)
                except Exception:
                    try:
                        from farkle.settings import TOOLTIP_BUTTON_DELAY_MS as _OLD_BTN_DELAY
                        delay_override = int(_OLD_BTN_DELAY)
                    except Exception:
                        pass
                return {"title": btn.label, "lines": lines, "delay_ms": delay_override, "target": btn.rect.copy(), "id": f"btn_{btn.name}"}
    except Exception:
        pass
    # 5. Relic panel (active relics list)
    try:
        for obj in getattr(game, 'ui_misc', []):
            if getattr(obj, 'name', None) == 'RelicPanel':
                rrect = getattr(obj, '_last_rect', None)
                if rrect and rrect.collidepoint(mx,my):
                    # Use renderer helper to list active relics
                    try:
                        rm = getattr(game, 'relic_manager', None)
                        lines = rm.active_relic_lines() if rm else ["Relics: (manager missing)"]
                    except Exception:
                        lines = ["(error)"]
                    return {"title": "Active Relics", "lines": lines, "target": rrect.copy(), "id": "relic_panel"}
    except Exception:
        pass
    # 6. Help icon
    try:
        for obj in getattr(game, 'ui_misc', []):
            if getattr(obj, 'name', None) == 'HelpIcon' and getattr(obj, 'rect', None) and obj.rect.collidepoint(mx,my):
                return {"title": "Help", "lines": ["Click to toggle rules overlay."], "target": obj.rect.copy(), "id": "help_icon"}
    except Exception:
        pass
    return None
