from dataclasses import dataclass, field
from typing import List, Optional
import pygame
from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import TEXT_PRIMARY, TEXT_ACCENT, HEIGHT

# Gods progression constants
GOD_MAX_LEVEL = 3

@dataclass
class God(GameObject):
    name: str = ""
    # For future: each god can have a modifier_chain (selective effects). Start empty.
    def __init__(self, name: str, game=None):
        super().__init__(name=name)
        self.game = game
        # Lazy import to avoid cycles
        from farkle.scoring.score_modifiers import ScoreModifierChain
        self.modifier_chain = ScoreModifierChain()
        # UI state managed by GodsManager during draw
        self._rect: Optional[pygame.Rect] = None
        # Progression
        self.level: int = 1

    def draw(self, surface):  # type: ignore[override]
        # Draw the label for this god at its assigned rect
        if not self._rect:
            return None
        g = getattr(self, 'game', None)
        if not g:
            return None
        display = f"{self.name}"
        color = TEXT_ACCENT
        try:
            surf = g.font.render(display, True, color)
            surface.blit(surf, self._rect.topleft)
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
