import pygame
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import (
    DICE_SIZE, BG_COLOR, REROLL_BTN
)
from farkle.ui.modal_stack import ModalStack

class GameRenderer:
    def __init__(self, game):
        self.game = game
        # Shop panel dimensions (enlarged)
        self.SHOP_PANEL_WIDTH = 600
        self.SHOP_PANEL_HEIGHT = 340
        # Help overlay state
        self.help_icon_rect = pygame.Rect(10, self.game.screen.get_height() - 50, 40, 40)
        self.show_help = False
        # Sprite layering groups (initially empty). We keep existing draw path until dice sprites added.
        # LayeredUpdates respects each sprite._layer.
        self.layered = pygame.sprite.LayeredUpdates()
        # Convenience subgroup references by semantic purpose (will share membership in layered)
        self.sprite_groups = {
            'world': pygame.sprite.Group(),
            'dice': pygame.sprite.Group(),
            'ui': pygame.sprite.Group(),
            'overlay': pygame.sprite.Group(),
            'modal': pygame.sprite.Group(),
        }
        # NOTE: For now we do not call layered.draw(); we wait until at least dice migrated to sprites.
        # Modal stack placeholder (overlays like future shop popup)
        self.modal_stack = ModalStack()
    # Renderer focuses on core gameplay visuals; shop interaction rendered by ShopScreen / ShopOverlaySprite.



    # Internal helper so click handling can ensure rects exist even before first post-open draw flip

    def handle_click(self, game, pos):
        """Delegate click handling to game logic; renderer no longer performs selection logic."""
        g = game
        mx, my = pos
        consumed = False
    # If shop is open, let ShopOverlaySprite consume interactions before normal UI.
        if getattr(g, 'relic_manager', None) and g.relic_manager.shop_open:
            # Delegate to shop overlay sprite for unit tests invoking renderer directly
            try:
                spr = getattr(g, 'shop_overlay_sprite', None)
                if spr and hasattr(spr, 'handle_click'):
                    if spr.handle_click(g, (mx,my)):
                        return True
            except Exception:
                pass
            return True
    # Route clicks to logical buttons (sprites mirror their rects) when shop not intercepting.
        for btn in getattr(g, 'ui_buttons', []):
            try:
                # Skip if button not visible in current state
                st = g.state_manager.get_state()
                if hasattr(btn, 'visible_states') and st not in btn.visible_states:
                    continue
                if btn.rect.collidepoint(mx, my):
                    # Delegate to UIButton logic (publishes appropriate REQUEST_* events)
                    btn.handle_click(g, (mx, my))
                    return True
            except Exception:
                continue
        # Help icon toggle (lowest priority so gameplay UI still works when overlay open)
        if self.help_icon_rect.collidepoint(mx, my):
            self.show_help = not self.show_help
            return True
    # Shop handled elsewhere; if open we already returned above.
        if getattr(g, 'relic_manager', None) and g.relic_manager.shop_open:
            return False

    # Check if we're in target selection mode
        in_target_selection = g.state_manager.get_state() == g.state_manager.state.SELECTING_TARGETS
        
        # Goal selection via each goal's cached rect from last draw
        # Skip fulfilled goals - they can't receive more points
        # In target selection mode, check if ability targets goals first
        if in_target_selection:
            abm = getattr(g, 'ability_manager', None)
            selecting_ability = abm.selecting_ability() if abm else None
            if selecting_ability and selecting_ability.target_type == 'goal':
                # Let goal sprites handle clicks during goal-targeting
                for idx, goal in enumerate(g.level_state.goals):
                    rect = getattr(goal, '_last_rect', None)
                    if rect and rect.collidepoint(mx, my):
                        # Goal sprite should handle this via its handle_click
                        # which calls attempt_target
                        if abm.attempt_target('goal', idx):
                            return True
                        break
                return consumed
        
        # Normal goal selection (not in target selection mode)
        if not in_target_selection:
            for idx, goal in enumerate(g.level_state.goals):
                rect = getattr(goal, '_last_rect', None)
                if rect and rect.collidepoint(mx, my):
                    # Only allow selecting non-fulfilled goals
                    if not goal.is_fulfilled():
                        g.active_goal_index = idx
                        consumed = True
                    break
        
        # Dice selection handled centrally by Game._handle_die_click
        # Only allow dice selection during SELECTING_TARGETS if ability targets dice
        if in_target_selection:
            abm = getattr(g, 'ability_manager', None)
            selecting_ability = abm.selecting_ability() if abm else None
            if selecting_ability and selecting_ability.target_type == 'die':
                # Allow dice clicks - they'll be handled by _handle_die_click
                if g._handle_die_click(mx, my, button=1):
                    consumed = True
        else:
            # Normal dice selection (not in target selection mode)
            if g._handle_die_click(mx, my, button=1):
                consumed = True
        
        return consumed

    # Button state & selection preview logic migrated to Game / button factories.
    def draw(self):
        g = self.game
        screen = g.screen
        screen.fill(BG_COLOR)
        shop_open = bool(getattr(g, 'relic_manager', None) and g.relic_manager.shop_open)
    # Dim background when shop open; rest of UI draws unchanged.
        abm = getattr(g, 'ability_manager', None)
        selecting_reroll = (g.state_manager.get_state() == g.state_manager.state.SELECTING_TARGETS and abm and abm.selecting_ability() and abm.selecting_ability().id == 'reroll')
    # Perform dynamic button layout before sprite sync so button sprites update same frame.
        try:
            dice = getattr(g, 'dice', [])
            if dice:
                left = min(getattr(d, 'x') for d in dice)
                right = max(getattr(d, 'x') + getattr(d, 'size', DICE_SIZE) for d in dice)
                bottom = max(getattr(d, 'y') + getattr(d, 'size', DICE_SIZE) for d in dice)
                roll_btn = next((b for b in g.ui_buttons if b.name == 'roll'), None)
                bank_btn = next((b for b in g.ui_buttons if b.name == 'bank'), None)
                next_btn = next((b for b in g.ui_buttons if b.name == 'next'), None)
                if roll_btn:
                    import pygame as _pg
                    padding = 8
                    new_width = max(160, (right - left) + padding * 2)
                    new_height = 56
                    new_x = left - padding
                    if new_x < 10: new_x = 10
                    new_y = bottom + 22
                    from farkle.ui.settings import HEIGHT as _H
                    if new_y + new_height + 10 > _H:
                        new_y = _H - new_height - 10
                    roll_btn.rect = _pg.Rect(new_x, new_y, new_width, new_height)
                    if bank_btn:
                        spacing_y = 10
                        bank_y = roll_btn.rect.bottom + spacing_y
                        if bank_y + new_height + 10 > _H:
                            bank_y = _H - new_height - 10
                        bank_btn.rect = _pg.Rect(new_x, bank_y, new_width, new_height)
                if next_btn:
                    st = g.state_manager.get_state()
                    import pygame as _pg
                    padding = 8
                    if st in (g.state_manager.state.FARKLE, g.state_manager.state.BANKED):
                        new_width = max(160, (right - left) + padding * 2)
                        new_height = 56
                        new_x = left - padding
                        if new_x < 10: new_x = 10
                        # Next button sits directly below dice row
                        base_y = bottom + 22
                        from farkle.ui.settings import HEIGHT as _H
                        if base_y + new_height + 10 > _H:
                            base_y = _H - new_height - 10
                        next_btn.rect = _pg.Rect(new_x, base_y, new_width, new_height)
                        # If roll button exists, push it further down below banner placeholder
                        if roll_btn and hasattr(roll_btn, 'rect'):
                            roll_btn.rect.y = next_btn.rect.bottom + 72  # space for banner (56) + margin
                        if bank_btn and hasattr(bank_btn, 'rect'):
                            bank_btn.rect.y = roll_btn.rect.bottom + 10 if roll_btn else next_btn.rect.bottom + 72
        except Exception:
            pass
        
        # Sync all sprites (dice, buttons, goals, HUD, overlays) AFTER layout changes.
        try:
            self.layered.update()
            
            # LayeredUpdates doesn't maintain sort order when sprites added dynamically during update.
            # Rebuild the group in proper layer order.
            if getattr(g, 'choice_window_sprite', None):
                cw = g.choice_window_sprite
                if cw.choice_window and cw.choice_window.is_open():
                    # Collect all sprites and re-add in sorted order
                    all_sprites = list(self.layered.sprites())
                    self.layered.empty()
                    # Sort by layer (ascending) so higher layers draw last (on top)
                    all_sprites.sort(key=lambda s: s._layer)
                    for sprite in all_sprites:
                        self.layered.add(sprite)
            
            self.layered.draw(screen)
        except Exception:
            pass
        # Skip drawing non-dice dynamic UI when shop open
        for obj in getattr(g, 'ui_dynamic', []):
            if obj.__class__.__name__ == 'Die':
                continue  # dice sprite-driven
            if shop_open:
                continue
            try:
                if hasattr(obj, 'should_draw') and not obj.should_draw(g):
                    continue
                obj.draw(screen)  # type: ignore[attr-defined]
            except Exception:
                pass
        # Reroll selection overlay highlight over applicable dice (still manual until sprite effect added)
        # Reroll highlight now handled by DieSprite overlay logic.
        # (Button dynamic layout now occurs before sprite update; legacy block removed.)
        # Draw buttons via GameObjects
        # (Button drawing handled by UIButtonSprite now.)
        # (Status message, turn score, and selection preview removed per new minimal UI requirement.)
        # Goal drawing handled by GoalSprite instances.
        # Gods panel is drawn via a GameObject added to ui_misc
        if not shop_open:
            screen.blit(g.font.render(f"Level {g.level_index}", True, (180, 220, 255)), (10, 10))
        # Legacy goal draw removed if sprites exist; if any goal lacks sprite fallback to old approach
        # Fallback goal draw removed; all goals expected to have sprites.
        # Note: display flipping is performed in App.run() (single flip per frame). Renderer does not flip.
        # Bottom status message near help icon (small font). Truncate if too long.
        if not shop_open:
            try:
                msg = getattr(g, 'message', '') or ''
                font_small = getattr(g, 'small_font', g.font)
                max_width = 360
                surf = font_small.render(msg, True, (230,235,240))
                if surf.get_width() > max_width:
                    ellipsis = '…'
                    low, high = 0, len(msg)
                    fit = ''
                    while low <= high:
                        mid = (low + high)//2
                        test = msg[:mid] + ellipsis
                        if font_small.render(test, True, (230,235,240)).get_width() <= max_width:
                            fit = test
                            low = mid + 1
                        else:
                            high = mid - 1
                    surf = font_small.render(fit, True, (230,235,240))
                pad = 8
                y = screen.get_height() - surf.get_height() - pad
                x = 60
                screen.blit(surf, (x, y))
            except Exception:
                pass
        # Shop overlay (in-place) if open: draw modal panel over gameplay
        # Shop overlay now fully handled by ShopOverlaySprite; legacy inline draw removed.

# Note: Avoid importing Game for type checking to prevent circular dependency.
