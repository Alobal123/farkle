"""Sprites for rendering choice windows."""

import pygame
from typing import List, Tuple
from farkle.ui.sprites.sprite_base import BaseSprite, Layer
from farkle.ui.choice_window import ChoiceWindow, ChoiceWindowState


class GodChoiceItemSprite(BaseSprite):
    """Sprite for rendering a god choice item using the god's draw_card method."""
    
    def __init__(self, item, god, game, *groups):
        super().__init__(Layer.TOOLTIP, item, *groups)  # Above MODAL to appear on top of choice window
        self.item = item
        self.god = god  # Temporary god instance for rendering
        self.game = game
        # Only visible when choice window is open AND maximized
        self.visible_predicate = lambda g: (
            hasattr(g, 'choice_window_manager') and 
            g.choice_window_manager.active_window and 
            g.choice_window_manager.active_window.is_open() and
            g.choice_window_manager.active_window.state == ChoiceWindowState.MAXIMIZED
        )
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sync_from_logical()
    
    def update(self, *args, **kwargs):
        """Override update to correctly pass game instance for visibility checking."""
        game = self.game
        if self.visible_states or self.visible_predicate:
            try:
                st = game.state_manager.get_state()
                allowed = True
                if self.visible_states and st not in self.visible_states:
                    allowed = False
                if allowed and self.visible_predicate and not self.visible_predicate(game):
                    allowed = False
                if not allowed:
                    # Hide sprite; keep off-screen to avoid interaction
                    if self.image.get_width() != 1 or self.image.get_height() != 1:
                        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
                        self.rect = self.image.get_rect(topleft=(-1000,-1000))
                    else:
                        self.image.fill((0,0,0,0))
                    self.dirty = 1
                    return
            except Exception:
                pass
        self.sync_from_logical()
    
    def sync_from_logical(self):
        """Render the god choice card using god's draw_card method."""
        item = self.item
        god = self.god
        g = self.game
        
        card_width = 220
        card_height = 200
        
        # Preserve rect position when recreating image
        old_topleft = self.rect.topleft
        
        self.image = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=old_topleft)
        box_rect = self.image.get_rect()  # Local rect for drawing (0, 0 based)
        
        # Check if this god is selected (in the window's selected_indices)
        selected = False
        if hasattr(g, 'choice_window_manager') and g.choice_window_manager.active_window:
            window = g.choice_window_manager.active_window
            try:
                idx = window.items.index(item)
                selected = idx in window.selected_indices
            except (ValueError, AttributeError):
                pass
        
        # Use god's draw_card method to render the card
        god.draw_card(self.image, box_rect, g.font, g.small_font, selected=selected)
        
        self.dirty = 1


class ChoiceItemSprite(BaseSprite):
    """Sprite for rendering a single choice item."""
    
    def __init__(self, item, game, *groups):
        super().__init__(Layer.TOOLTIP, item, *groups)  # Above MODAL to appear on top of choice window
        self.item = item
        self.game = game
        # Only visible when choice window is open AND maximized
        self.visible_predicate = lambda g: (
            hasattr(g, 'choice_window_manager') and 
            g.choice_window_manager.active_window and 
            g.choice_window_manager.active_window.is_open() and
            g.choice_window_manager.active_window.state == ChoiceWindowState.MAXIMIZED
        )
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sync_from_logical()
    
    def update(self, *args, **kwargs):
        """Override update to correctly pass game instance for visibility checking."""
        game = self.game
        if self.visible_states or self.visible_predicate:
            try:
                st = game.state_manager.get_state()
                allowed = True
                if self.visible_states and st not in self.visible_states:
                    allowed = False
                if allowed and self.visible_predicate and not self.visible_predicate(game):
                    allowed = False
                if not allowed:
                    # Hide sprite; keep off-screen to avoid interaction
                    if self.image.get_width() != 1 or self.image.get_height() != 1:
                        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
                        self.rect = self.image.get_rect(topleft=(-1000,-1000))
                    else:
                        self.image.fill((0,0,0,0))
                    self.dirty = 1
                    return
            except Exception:
                pass
        self.sync_from_logical()
    
    def sync_from_logical(self):
        """Render the choice item card."""
        item = self.item
        g = self.game
        
        card_width = 220
        card_height = 200
        
        # Preserve rect position when recreating image
        old_topleft = self.rect.topleft
        
        self.image = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=old_topleft)
        box_rect = self.image.get_rect()  # Local rect for drawing (0, 0 based)
        
        # Card background
        bg_color = (65, 90, 120) if item.enabled else (45, 55, 65)
        pygame.draw.rect(self.image, bg_color, box_rect, border_radius=8)
        pygame.draw.rect(self.image, (120, 170, 210), box_rect, width=2, border_radius=8)
        
        y = box_rect.y + 12
        
        # Item name
        name_color = (255, 255, 255) if item.enabled else (140, 140, 140)
        name_surf = g.font.render(item.name, True, name_color)
        self.image.blit(name_surf, (box_rect.x + 10, y))
        y += name_surf.get_height() + 8
        
        # Description with text wrapping
        desc_font = g.small_font
        desc_color = (210, 210, 210) if item.enabled else (120, 120, 120)
        line_spacing = desc_font.get_linesize()
        max_width = box_rect.width - 20
        
        description = item.effect_text or item.description
        words = description.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if desc_font.size(test_line)[0] < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)
        
        # Reserve space for button and cost at bottom
        btn_height = 36
        cost_height = desc_font.get_height() + 5 if item.cost is not None else 0
        footer_height = btn_height + cost_height + 20
        max_desc_y = box_rect.height - footer_height
        
        for line in lines:
            if y + line_spacing > max_desc_y:
                break
            line_surf = desc_font.render(line.strip(), True, desc_color)
            self.image.blit(line_surf, (box_rect.x + 10, y))
            y += line_spacing
        
        # Bottom section: cost and select button
        # Cost (if applicable)
        if item.cost is not None:
            cost_y = box_rect.bottom - btn_height - cost_height - 15
            cost_text = f"Cost: {item.cost}g"
            cost_surf = desc_font.render(cost_text, True, (230, 210, 100))
            self.image.blit(cost_surf, (box_rect.x + 10, cost_y))
        
        # Select button
        btn_y = box_rect.bottom - btn_height - 10
        btn_rect = pygame.Rect(box_rect.x + 10, btn_y, box_rect.width - 20, btn_height)
        
        if item.enabled:
            btn_color = (80, 200, 110)
            btn_text_color = (0, 0, 0)
            btn_text = "Select"
        else:
            btn_color = (60, 70, 80)
            btn_text_color = (100, 100, 100)
            btn_text = "Unavailable"
        
        pygame.draw.rect(self.image, btn_color, btn_rect, border_radius=6)
        btn_surf = desc_font.render(btn_text, True, btn_text_color)
        self.image.blit(btn_surf, (
            btn_rect.centerx - btn_surf.get_width() // 2,
            btn_rect.centery - btn_surf.get_height() // 2
        ))
        
        self.dirty = 1


class ChoiceWindowSprite(BaseSprite):
    """Sprite for rendering the entire choice window with minimize/maximize support."""
    
    def __init__(self, choice_window, game, *groups):
        super().__init__(Layer.MODAL, choice_window, *groups)
        self.choice_window = choice_window
        self.game = game
        
        from farkle.ui.settings import WIDTH, HEIGHT
        self.screen_width = WIDTH
        self.screen_height = HEIGHT
        
        self.image = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(0, 0))
        
        self._item_sprites: List[BaseSprite] = []  # Can be GodChoiceItemSprite or ChoiceItemSprite
        self._minimize_rect = None
        self._skip_rect = None
        self._confirm_rect = None
        self._item_button_rects: List[Tuple[int, pygame.Rect]] = []
        self._minimized_icon_rect = None
        self._last_items_id = None  # Track if items changed
        
        # Visible only when window is open
        self.visible_predicate = lambda g: (
            self.choice_window and self.choice_window.is_open()
        )
        
        self.sync_from_logical()
    
    def update(self, *args, **kwargs):
        """Override update to correctly pass game instance for visibility checking."""
        game = self.game
        if self.visible_states or self.visible_predicate:
            try:
                st = game.state_manager.get_state()
                allowed = True
                if self.visible_states and st not in self.visible_states:
                    allowed = False
                if allowed and self.visible_predicate and not self.visible_predicate(game):
                    allowed = False
                if not allowed:
                    # Hide sprite; keep off-screen to avoid interaction
                    if self.image.get_width() != 1 or self.image.get_height() != 1:
                        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
                        self.rect = self.image.get_rect(topleft=(-1000,-1000))
                    else:
                        self.image.fill((0,0,0,0))
                    self.dirty = 1
                    return
            except Exception:
                pass
        self.sync_from_logical()
    
    def sync_from_logical(self):
        """Render the choice window based on its current state."""
        window = self.choice_window
        g = self.game
        
        if not window or not window.is_open():
            self.image.fill((0, 0, 0, 0))
            self._clear_item_sprites()
            self.dirty = 1
            return
        
        if window.is_minimized():
            self._render_minimized()
        else:
            self._render_maximized()
        
        self.dirty = 1
    
    def _render_minimized(self):
        """Render the minimized state (small icon in corner)."""
        self.image.fill((0, 0, 0, 0))
        self._clear_item_sprites()
        
        # Create a small icon in the bottom-right corner
        icon_width = 180
        icon_height = 50
        margin = 20
        
        icon_x = self.screen_width - icon_width - margin
        icon_y = self.screen_height - icon_height - margin
        
        icon_rect = pygame.Rect(icon_x, icon_y, icon_width, icon_height)
        self._minimized_icon_rect = icon_rect
        
        # Draw the minimized window
        pygame.draw.rect(self.image, (50, 70, 95), icon_rect, border_radius=8)
        pygame.draw.rect(self.image, (120, 170, 210), icon_rect, width=2, border_radius=8)
        
        # Title text
        title_surf = self.game.small_font.render(self.choice_window.title, True, (255, 255, 255))
        title_x = icon_rect.centerx - title_surf.get_width() // 2
        title_y = icon_rect.centery - title_surf.get_height() // 2
        self.image.blit(title_surf, (title_x, title_y))
        
        # Maximize indicator (click to expand)
        hint_surf = self.game.small_font.render("(Click to expand)", True, (180, 180, 180))
        hint_x = icon_rect.centerx - hint_surf.get_width() // 2
        hint_y = title_y + title_surf.get_height() + 2
        self.image.blit(hint_surf, (hint_x, hint_y))
    
    def _render_maximized(self):
        """Render the maximized state (full window)."""
        window = self.choice_window
        g = self.game
        
        # Very light semi-transparent overlay - goals clearly visible
        self.image.fill((0, 0, 0, 0))
        dim = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        dim.fill((18, 28, 40, 80))  # Very transparent - goals clearly visible
        self.image.blit(dim, (0, 0))
        
        # Calculate panel dimensions
        card_width = 220
        card_height = 200
        num_items = len(window.items)
        spacing = 20
        
        header_height = 120  # Title + minimize button + padding
        footer_height = 80   # Skip/Confirm buttons + padding
        
        content_width = num_items * card_width + max(0, num_items - 1) * spacing
        panel_width = content_width + 80  # Horizontal padding
        panel_height = card_height + header_height + footer_height
        
        panel_x = (self.screen_width - panel_width) // 2
        panel_y = (self.screen_height - panel_height) // 2
        panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        
        # Panel background
        pygame.draw.rect(self.image, (50, 70, 95), panel, border_radius=12)
        pygame.draw.rect(self.image, (120, 170, 210), panel, width=2, border_radius=12)
        
        # Title
        title_surf = g.font.render(window.title, True, (255, 255, 255))
        title_x = panel.centerx - title_surf.get_width() // 2
        title_y = panel.y + 20
        self.image.blit(title_surf, (title_x, title_y))
        
        # Minimize button (top-right corner of panel)
        if window.allow_minimize:
            min_btn_size = 30
            min_btn_x = panel.right - min_btn_size - 15
            min_btn_y = panel.y + 15
            self._minimize_rect = pygame.Rect(min_btn_x, min_btn_y, min_btn_size, min_btn_size)
            
            pygame.draw.rect(self.image, (80, 110, 140), self._minimize_rect, border_radius=4)
            pygame.draw.rect(self.image, (140, 180, 220), self._minimize_rect, width=1, border_radius=4)
            
            # Minimize icon (horizontal line)
            line_y = self._minimize_rect.centery
            line_start_x = self._minimize_rect.left + 8
            line_end_x = self._minimize_rect.right - 8
            pygame.draw.line(self.image, (255, 255, 255), 
                           (line_start_x, line_y), (line_end_x, line_y), 2)
        else:
            self._minimize_rect = None
        
        # Render choice items
        self._ensure_item_sprites(window.items, panel, header_height)
        
        # Bottom buttons
        button_width = 120
        button_height = 40
        button_y = panel.bottom - button_height - 20
        button_spacing = 20
        
        # Calculate button positions (centered)
        num_buttons = 2 if window.allow_skip else 1
        total_button_width = num_buttons * button_width + (num_buttons - 1) * button_spacing
        buttons_start_x = panel.centerx - total_button_width // 2
        
        button_x = buttons_start_x
        
        # Confirm button
        can_confirm = window.can_confirm()
        confirm_color = (80, 200, 110) if can_confirm else (60, 80, 90)
        confirm_text_color = (0, 0, 0) if can_confirm else (120, 120, 120)
        
        self._confirm_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        pygame.draw.rect(self.image, confirm_color, self._confirm_rect, border_radius=8)
        
        confirm_text = "Confirm"
        confirm_surf = g.font.render(confirm_text, True, confirm_text_color)
        self.image.blit(confirm_surf, (
            self._confirm_rect.centerx - confirm_surf.get_width() // 2,
            self._confirm_rect.centery - confirm_surf.get_height() // 2
        ))
        
        button_x += button_width + button_spacing
        
        # Skip button
        if window.allow_skip:
            self._skip_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            pygame.draw.rect(self.image, (180, 80, 60), self._skip_rect, border_radius=8)
            
            skip_surf = g.font.render("Skip", True, (0, 0, 0))
            self.image.blit(skip_surf, (
                self._skip_rect.centerx - skip_surf.get_width() // 2,
                self._skip_rect.centery - skip_surf.get_height() // 2
            ))
        else:
            self._skip_rect = None
    
    def _ensure_item_sprites(self, items, panel_rect, header_height):
        """Create/update sprites for choice items."""
        g = self.game
        
        # Check if items changed - use id() to detect list changes
        current_items_id = id(items)
        
        # Check if sprites still exist and are alive (not killed)
        sprites_alive = all(sprite.alive() for sprite in self._item_sprites) if self._item_sprites else False
        
        if self._last_items_id == current_items_id and len(self._item_sprites) == len(items) and sprites_alive:
            # Items haven't changed and sprites are alive, just update positions
            card_width = 220
            card_height = 200
            spacing = 20
            items_start_y = panel_rect.y + header_height
            items_start_x = panel_rect.x + 40
            
            for idx, sprite in enumerate(self._item_sprites):
                item_x = items_start_x + idx * (card_width + spacing)
                sprite.rect.topleft = (item_x, items_start_y)
                # Trigger re-render for selection state changes
                sprite.sync_from_logical()
            return
        
        self._last_items_id = current_items_id
        
        # Clear existing sprites
        self._clear_item_sprites()
        self._item_button_rects.clear()
        
        card_width = 220
        card_height = 200
        spacing = 20
        
        items_start_y = panel_rect.y + header_height
        items_start_x = panel_rect.x + 40
        
        for idx, item in enumerate(items):
            item_x = items_start_x + idx * (card_width + spacing)
            
            # Check if this is a god choice - if so, use GodChoiceItemSprite
            from farkle.gods.gods_manager import God
            try:
                # Try to instantiate to check if it's a god class
                if hasattr(item.payload, '__mro__') and God in item.payload.__mro__:
                    # Create a temporary god instance for rendering (without activating)
                    temp_god = item.payload(game=None)
                    sprite = GodChoiceItemSprite(item, temp_god, g, self.groups())
                else:
                    sprite = ChoiceItemSprite(item, g, self.groups())
            except:
                # Fallback to generic choice item sprite
                sprite = ChoiceItemSprite(item, g, self.groups())
            
            sprite.rect.topleft = (item_x, items_start_y)
            self._item_sprites.append(sprite)
            
            # Store card rect for click detection (click anywhere on card to select)
            card_rect = pygame.Rect(item_x, items_start_y, card_width, card_height)
            self._item_button_rects.append((idx, card_rect))
    
    def _clear_item_sprites(self):
        """Remove all item sprites."""
        for sprite in self._item_sprites:
            sprite.kill()
        self._item_sprites.clear()
    
    def handle_click(self, game, pos) -> bool:
        """Handle mouse clicks on the choice window.
        
        Returns:
            True if click was handled, False otherwise
        """
        window = self.choice_window
        if not window or not window.is_open():
            return False
        
        mx, my = pos
        
        # Handle minimized state - click to maximize
        if window.is_minimized():
            if self._minimized_icon_rect and self._minimized_icon_rect.collidepoint(mx, my):
                from farkle.core.game_event import GameEvent, GameEventType
                window.maximize()
                self.sync_from_logical()
                game.event_listener.publish(GameEvent(
                    GameEventType.CHOICE_WINDOW_MAXIMIZED,
                    payload={"window_type": window.window_type}
                ))
                return True
            return False  # Don't swallow clicks when minimized
        
        # Handle maximized state
        # Check minimize button
        if self._minimize_rect and self._minimize_rect.collidepoint(mx, my):
            from farkle.core.game_event import GameEvent, GameEventType
            window.minimize()
            self.sync_from_logical()
            game.event_listener.publish(GameEvent(
                GameEventType.CHOICE_WINDOW_MINIMIZED,
                payload={"window_type": window.window_type}
            ))
            return True
        
        # Check item selection buttons
        for idx, btn_rect in self._item_button_rects:
            if btn_rect.collidepoint(mx, my):
                item = window.items[idx]
                if item.enabled:
                    from farkle.core.game_event import GameEvent, GameEventType
                    window.select_item(idx)
                    # Re-sync to update visual state immediately
                    self.sync_from_logical()
                    game.event_listener.publish(GameEvent(
                        GameEventType.CHOICE_ITEM_SELECTED,
                        payload={
                            "window_type": window.window_type,
                            "item_index": idx,
                            "item_id": item.id,
                            "item_name": item.name
                        }
                    ))
                    return True
        
        # Check confirm button
        if self._confirm_rect and self._confirm_rect.collidepoint(mx, my):
            if window.can_confirm():
                from farkle.core.game_event import GameEvent, GameEventType
                game.event_listener.publish(GameEvent(
                    GameEventType.REQUEST_CHOICE_CONFIRM,
                    payload={"window_type": window.window_type}
                ))
                return True
        
        # Check skip button
        if self._skip_rect and self._skip_rect.collidepoint(mx, my):
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish(GameEvent(
                GameEventType.REQUEST_CHOICE_SKIP,
                payload={"window_type": window.window_type}
            ))
            return True
        
        # Swallow all clicks while maximized
        return True


__all__ = ["ChoiceWindowSprite", "ChoiceItemSprite"]
