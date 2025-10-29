from dataclasses import dataclass, field
from typing import List, Optional
import pygame
from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import (
    TEXT_PRIMARY, TEXT_ACCENT, HEIGHT,
    CARD_BG_NORMAL, CARD_BG_SELECTED, CARD_BORDER_NORMAL, CARD_BORDER_SELECTED,
    CARD_GLOW_FILL, CARD_GLOW_BORDER, TEXT_WHITE, GOD_LORE_TEXT
)

# Gods progression constants
GOD_MAX_LEVEL = 3

@dataclass
class God(GameObject):
    name: str = ""
    lore: str = ""  # Lore text for choice window display
    description: str = ""  # Short description
    
    # For future: each god can have a modifier_chain (selective effects). Start empty.
    def __init__(self, name: str, game=None, lore: str = "", description: str = ""):
        super().__init__(name=name)
        self.game = game
        self.lore = lore
        self.description = description
        # Lazy import to avoid cycles
        from farkle.scoring.score_modifiers import ScoreModifierChain
        self.modifier_chain = ScoreModifierChain()
        # UI state managed by GodsManager during draw
        self._rect: Optional[pygame.Rect] = None
        # Progression
        self.level: int = 1
        self.progress: int = 0  # Generic progress counter for events

    def draw_card(self, surface: pygame.Surface, rect: pygame.Rect, font, small_font, selected: bool = False):
        """Draw a god card for choice windows or other displays.
        
        Args:
            surface: Surface to draw on
            rect: Rectangle to draw within
            font: Main font
            small_font: Small font for details
            selected: Whether this god is selected
        """
        # Card background with pronounced highlight when selected
        if selected:
            # Draw outer glow for selected card
            glow_rect = rect.inflate(8, 8)
            pygame.draw.rect(surface, CARD_GLOW_FILL, glow_rect, border_radius=10)
            pygame.draw.rect(surface, CARD_GLOW_BORDER, glow_rect, width=3, border_radius=10)
            
            bg_color = CARD_BG_SELECTED
            border_color = CARD_BORDER_SELECTED
            border_width = 4  # Thicker border
        else:
            bg_color = CARD_BG_NORMAL
            border_color = CARD_BORDER_NORMAL
            border_width = 2
        
        pygame.draw.rect(surface, bg_color, rect, border_radius=8)
        pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=8)
        
        y = rect.y + 12
        
        # Try to load and display god icon - much larger now
        from farkle.ui.god_icons import get_god_icon
        icon = get_god_icon(self.name)
        if icon:
            # Scale icon to be much larger (120x120 pixels)
            icon_size = 120
            scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
            
            # Center the icon horizontally
            icon_x = rect.x + (rect.width - icon_size) // 2
            surface.blit(scaled_icon, (icon_x, y))
            y += icon_size + 8
        
        # God name and level
        name_text = f"{self.name} (Lv{self.level})" if self.level > 0 else self.name
        name_surf = font.render(name_text, True, TEXT_WHITE)
        # Center the name horizontally
        name_x = rect.x + (rect.width - name_surf.get_width()) // 2
        surface.blit(name_surf, (name_x, y))
        y += name_surf.get_height() + 8
        
        # Lore text with wrapping
        if self.lore:
            line_spacing = small_font.get_linesize()
            max_width = rect.width - 20
            
            words = self.lore.split(' ')
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if small_font.size(test_line)[0] < max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word + " "
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                if y + line_spacing > rect.bottom - 10:
                    break
                line_surf = small_font.render(line.strip(), True, GOD_LORE_TEXT)
                surface.blit(line_surf, (rect.x + 10, y))
                y += line_spacing

    def draw(self, surface):  # type: ignore[override]
        # Draw the god icon and name in the gods panel
        if not self._rect:
            return None
        g = getattr(self, 'game', None)
        if not g:
            return None
        
        # Load and display god icon
        from farkle.ui.god_icons import get_god_icon
        icon = get_god_icon(self.name)
        
        x = self._rect.x
        y = self._rect.y
        
        if icon:
            # Scale icon to fit in the panel (48x48 pixels for panel display)
            icon_size = 48
            scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
            surface.blit(scaled_icon, (x, y))
            x += icon_size + 8  # Move text to the right of the icon
        
        # God name and level
        display = f"{self.name} (Lv{self.level})" if self.level > 0 else self.name
        color = TEXT_ACCENT
        try:
            surf = g.font.render(display, True, color)
            surface.blit(surf, (x, y + 12))  # Vertically center text relative to icon
        except Exception:
            pass
        return None


class GodsManager(GameObject):
    """Manages the currently worshipped gods.

    - Up to three gods are worshipped at a time (displayed in UI).
    - Each god implementation listens for specific events and levels up independently.
    - Effects are selective modifiers contributed via events (SCORE_MODIFIER_ADDED) and applied centrally by ScoringManager.
    """
    def __init__(self, game):
        super().__init__(name="GodsManager")
        self.game = game
        self.worshipped: List[God] = []
        self._god_name_rects: list[pygame.Rect] = []

    def set_worshipped(self, gods: List[God]):
        """Set the worshipped gods and activate them."""
        # Deactivate old gods
        for god in self.worshipped:
            if god.active:
                god.deactivate(self.game)
        
        # Set new gods
        self.worshipped = gods[:3]
        
        # Activate new gods
        for god in self.worshipped:
            if not god.active:
                god.activate(self.game)

    def on_event(self, event: GameEvent):  # type: ignore[override]
        # Gods no longer gain XP from scoring events
        # Each god implementation will listen for specific events and level up independently
        return

    def draw(self, surface):  # type: ignore[override]
        g = getattr(self, 'game', None)
        if not g or not self.worshipped:
            return
        # Detect shop state (we draw but dim when shop is open)
        in_shop = False
        try:
            if hasattr(g, 'relic_manager') and getattr(g.relic_manager, 'shop_open', False):
                in_shop = True
            st = g.state_manager.get_state()
            if st == g.state_manager.state.SHOP:
                in_shop = True
        except Exception:
            pass
        # Compute y below goals
        goals_bottom = 0
        for goal in g.level_state.goals:
            r = getattr(goal, '_last_rect', None)
            if r:
                goals_bottom = max(goals_bottom, r.bottom)
        y_start = (goals_bottom + 10) if goals_bottom > 0 else (HEIGHT // 2 + 80)
        x_start = 80
        label_surf = g.font.render("Gods:", True, TEXT_PRIMARY)
        surface.blit(label_surf, (x_start, y_start))
        # Names laid out horizontally with small spacing; assign rects then delegate draw to each god
        self._god_name_rects = []
        x = x_start + label_surf.get_width() + 10
        max_name_h = 0
        small_h = getattr(g, 'small_font', g.font).get_height()
        for i, god in enumerate(self.worshipped):
            # Compute size from current label (with level) to advance x; God will render itself
            base_display = f"{god.name} Lv{god.level}"
            try:
                surf = g.font.render(base_display, True, TEXT_ACCENT)
                rect = surf.get_rect()
            except Exception:
                rect = pygame.Rect(0, 0, 60, 20)
                surf = None
            rect.topleft = (x, y_start)
            # Update per-god UI state
            god._rect = rect
            # Delegate draw to the god
            try:
                god.draw(surface)
            except Exception:
                pass
            self._god_name_rects.append(rect)
            if surf is not None:
                try:
                    max_name_h = max(max_name_h, surf.get_height())
                except Exception:
                    pass
            x += rect.width + 12

        # If in shop, overlay a translucent dim over the gods panel area
        if in_shop:
            try:
                total_w = max(0, x - x_start)
                # Name height only (no XP bar anymore)
                panel_h = max_name_h + 4
                if total_w > 0 and panel_h > 0:
                    overlay = pygame.Surface((total_w, panel_h), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 120))
                    surface.blit(overlay, (x_start, y_start))
            except Exception:
                pass

    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        # No longer handle god switching clicks
        return False
