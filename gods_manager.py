from dataclasses import dataclass, field
from typing import List, Optional
import pygame
from game_object import GameObject
from game_event import GameEvent, GameEventType
from settings import TEXT_PRIMARY, TEXT_ACCENT, HEIGHT

# Gods progression constants
GOD_MAX_LEVEL = 10
# XP required to advance from level N to N+1 (indices 0..8 correspond to levels 1..9)
GOD_XP_TO_LEVEL = [100, 150, 200, 250, 300, 350, 400, 450, 500]

@dataclass
class God(GameObject):
    name: str = ""
    # For future: each god can have a modifier_chain (selective effects). Start empty.
    def __init__(self, name: str):
        super().__init__(name=name)
        # Lazy import to avoid cycles
        from score_modifiers import ScoreModifierChain
        self.modifier_chain = ScoreModifierChain()
        # UI state managed by GodsManager during draw
        self._rect: Optional[pygame.Rect] = None
        self._active: bool = False
        # Progression
        self.level: int = 1
        self.xp: int = 0

    def draw(self, surface):  # type: ignore[override]
        # Draw the label for this god at its assigned rect
        if not self._rect:
            return None
        g = getattr(self, 'game', None)
        if not g:
            return None
        display = f"[{self.name} Lv{self.level}]" if self._active else f"{self.name} Lv{self.level}"
        color = (240, 230, 140) if self._active else TEXT_ACCENT
        try:
            surf = g.font.render(display, True, color)
            surface.blit(surf, self._rect.topleft)
            # XP progress (below name)
            xp_req = self.xp_required_for_next()
            if xp_req > 0:
                xp_text = f"XP {self.xp}/{xp_req}"
            else:
                xp_text = "MAX"
            small = getattr(g, 'small_font', g.font)
            xp_surf = small.render(xp_text, True, TEXT_PRIMARY)
            xp_pos = (self._rect.x, self._rect.y + surf.get_height() + 2)
            surface.blit(xp_surf, xp_pos)
            # XP bar under the XP text
            bar_margin_top = 2
            bar_x = self._rect.x
            bar_y = xp_pos[1] + xp_surf.get_height() + bar_margin_top
            # Choose a reasonable width based on name width, min 80, max 160
            bar_w = max(80, min(160, surf.get_width()))
            bar_h = 6
            # Background
            pygame.draw.rect(surface, (50, 60, 70), pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=3)
            # Border
            pygame.draw.rect(surface, (90, 110, 130), pygame.Rect(bar_x, bar_y, bar_w, bar_h), width=1, border_radius=3)
            # Fill proportion
            if xp_req > 0:
                pct = max(0.0, min(1.0, self.xp / float(xp_req)))
            else:
                pct = 1.0  # MAX
            fill_w = int(bar_w * pct)
            if fill_w > 0:
                fill_color = (240, 230, 140) if xp_req == 0 else (90, 200, 110)
                pygame.draw.rect(surface, fill_color, pygame.Rect(bar_x, bar_y, fill_w, bar_h), border_radius=3)
        except Exception:
            pass
        return None

    # Progression helpers
    def xp_required_for_next(self) -> int:
        if self.level >= GOD_MAX_LEVEL:
            return 0
        idx = max(0, min(self.level - 1, len(GOD_XP_TO_LEVEL) - 1))
        return GOD_XP_TO_LEVEL[idx]

    def add_xp(self, amount: int) -> None:
        if amount <= 0 or self.level >= GOD_MAX_LEVEL:
            return
        self.xp += int(amount)
        # Handle multiple level-ups if enough XP
        leveled = False
        while self.level < GOD_MAX_LEVEL:
            req = self.xp_required_for_next()
            if req <= 0 or self.xp < req:
                break
            self.xp -= req
            self.level += 1
            leveled = True
        if self.level >= GOD_MAX_LEVEL:
            # Clamp XP at 0 for max level display
            self.xp = 0
        if leveled:
            # Publish a message on level-up
            try:
                from game_event import GameEvent as GE, GameEventType as GET
                if getattr(self, 'game', None):
                    self.game.event_listener.publish(GE(GET.MESSAGE, payload={"text": f"{self.name} reached Lv{self.level}"}))  # type: ignore[attr-defined]
            except Exception:
                pass

    def apply_selective(self, score_obj) -> None:
        """Apply this god's selective modifiers to the provided score_obj if any.

        Global multipliers are removed from the game; only selective part modifiers may be used.
        """
        if not score_obj:
            return
        try:
            base = getattr(score_obj, 'total_effective', 0)
            # Build a concrete context that satisfies ScoreContext Protocol
            class _GodScoreContext:
                def __init__(self, score_obj, pending_raw: int):
                    self.score_obj = score_obj
                    self.pending_raw = pending_raw
            context = _GodScoreContext(score_obj, base)
            for m in self.modifier_chain.snapshot():  # type: ignore[attr-defined]
                try:
                    _ = m.apply(base, context)
                except Exception:
                    pass
        except Exception:
            pass


class GodsManager(GameObject):
    """Manages the currently worshipped gods and which one is active (prayed to).

    - Up to three gods are worshipped at a time (displayed in UI).
    - Only one god can be active; only the active god's effects apply to score events.
    - Effects are selective modifiers applied during SCORE_PRE_MODIFIERS so previews and final scoring align.
    """
    def __init__(self, game):
        super().__init__(name="GodsManager")
        self.game = game
        self.worshipped: List[God] = []
        self.active_index: int = 0
        self._god_name_rects: list[pygame.Rect] = []

    def set_worshipped(self, gods: List[God]):
        self.worshipped = gods[:3]
        if self.active_index >= len(self.worshipped):
            self.active_index = 0 if self.worshipped else -1
        # Ensure gods know the game reference for drawing
        for gd in self.worshipped:
            try:
                gd.game = self.game  # type: ignore[attr-defined]
            except Exception:
                pass

    def active_god(self) -> Optional[God]:
        if 0 <= self.active_index < len(self.worshipped):
            return self.worshipped[self.active_index]
        return None

    def select_active(self, index: int) -> None:
        if 0 <= index < len(self.worshipped):
            self.active_index = index
            try:
                from game_event import GameEvent as GE, GameEventType as GET
                self.game.event_listener.publish(GE(GET.MESSAGE, payload={"text": f"Praying to {self.worshipped[index].name}"}))
            except Exception:
                pass

    def on_event(self, event: GameEvent):  # type: ignore[override]
        if event.type == GameEventType.SCORE_PRE_MODIFIERS:
            # Apply active god's selective modifiers to score_obj
            score_obj = event.get('score_obj')
            g = self.active_god()
            if g and score_obj is not None:
                g.apply_selective(score_obj)
        elif event.type == GameEventType.SCORE_APPLIED:
            # Award XP to active god equal to applied adjusted points
            adjusted = int(event.get('adjusted', 0) or 0)
            if adjusted > 0:
                g = self.active_god()
                if g is not None:
                    g.add_xp(adjusted)
        # No other event handling yet
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
            display = f"[{base_display}]" if i == self.active_index else base_display
            try:
                surf = g.font.render(display, True, TEXT_ACCENT)
                rect = surf.get_rect()
            except Exception:
                rect = pygame.Rect(0, 0, 60, 20)
                surf = None
            rect.topleft = (x, y_start)
            # Update per-god UI state
            god._rect = rect
            god._active = (i == self.active_index)
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
                # Name height + xp text height + spacing + bar height (6)
                panel_h = max_name_h + 2 + small_h + 2 + 6
                if total_w > 0 and panel_h > 0:
                    overlay = pygame.Surface((total_w, panel_h), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 120))
                    surface.blit(overlay, (x_start, y_start))
            except Exception:
                pass

    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        mx, my = pos
        if not self.worshipped:
            return False
        # Ignore clicks during shop
        try:
            if hasattr(game, 'relic_manager') and getattr(game.relic_manager, 'shop_open', False):
                return False
            st = game.state_manager.get_state()
            if st == game.state_manager.state.SHOP:
                return False
        except Exception:
            pass
        # Prefer per-god rects for click detection
        for i, god in enumerate(self.worshipped):
            r = getattr(god, '_rect', None)
            if r and r.collidepoint(mx, my):
                self.select_active(i)
                return True
        return False
