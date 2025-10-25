import pygame
from .base_screen import SimpleScreen
from farkle.game import Game

class GameScreen(SimpleScreen):
    """Screen wrapper around the core `Game` object.

    Responsibilities:
    - Delegate event handling to Game._process_event_single
    - Call Game._step_frame each update to advance one frame
    - Provide Screen protocol surface for App so all screens uniform
        Transition Logic:
    - This screen never marks itself done internally; App switches to other screens
      on events (e.g., LEVEL_ADVANCE_FINISHED -> 'shop').
            Tooltip & Key Handling:
            - Hover/tooltip timing & rendering and gameplay hotkeys (shop skip ESC/S, cancel
                ability targeting ESC) live here, keeping `Game` focused purely on state & events.
    """
    def __init__(self, game: Game):
        super().__init__()
        self.game = game
        # Tooltip state moved from Game
        self._last_mouse_pos: tuple[int,int] = (0,0)
        self._hover_anchor_pos: tuple[int,int] = (0,0)
        self._hover_start_ms: int = 0
        self._current_tooltip: dict | None = None
        # Anti-flicker tracking: retain tooltip through brief resolution misses
        self._miss_frames: int = 0
        self._grace_frames: int = 5  # number of consecutive misses allowed before hiding
        self._visible_since_ms: int = 0  # time when current tooltip became visible
        # Caching: store last resolved tooltip target and data to avoid repeated resolution every frame
        self._cached_tip: dict | None = None
        self._cached_target_rect = None
        # Minimum visible duration (ms) before allowing hide after leaving target (except large movement)
        self._min_visible_ms: int = 200
        # Extra margin around target rect for retention tolerance
        self._target_margin = 8

    def handle_event(self, event: pygame.event.Event) -> None:  # type: ignore[override]
        import pygame as _pg
        if event.type == pygame.MOUSEMOTION:
            self._last_mouse_pos = event.pos
            # Jitter threshold: ignore tiny movements (<3px) to avoid resetting hover timer
            dx = abs(event.pos[0] - self._hover_anchor_pos[0])
            dy = abs(event.pos[1] - self._hover_anchor_pos[1])
            jitter_threshold = 3
            if dx > jitter_threshold or dy > jitter_threshold:
                self._hover_anchor_pos = event.pos
                self._hover_start_ms = _pg.time.get_ticks()
                # Invalidate tooltip on significant movement. The draw loop will re-evaluate.
                self._current_tooltip = None
            # Pass through to game only for non-tooltip concerns
            return
        if event.type == pygame.KEYDOWN:
            # Shop skip hotkeys
            if self.game.relic_manager.shop_open and event.key in (pygame.K_ESCAPE, pygame.K_s):
                try:
                    from farkle.core.game_event import GameEvent, GameEventType
                    self.game.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP))
                except Exception:
                    pass
            # Ability target selection cancel
            if event.key == pygame.K_ESCAPE and self.game.state_manager.get_state() == self.game.state_manager.state.SELECTING_TARGETS:
                self.game.cancel_target_selection(reason="cancelled")
            return
        # Delegate remaining events to Game
        self.game._process_event_single(event)

    def update(self, dt: float) -> None:  # type: ignore[override]
        # Nothing time-based yet; frame progression handled in draw call
        pass

    def draw(self, surface: pygame.Surface) -> None:  # type: ignore[override]
        # Resolve tooltip then ask game to draw
        import pygame as _pg
        try:
            from farkle.ui.settings import TOOLTIP_DELAY_MS, TOOLTIP_BG_COLOR, TOOLTIP_BORDER_COLOR, WIDTH, HEIGHT
            elapsed = _pg.time.get_ticks() - self._hover_start_ms
            
            try:
                from farkle.ui.tooltip import resolve_hover
                tip = resolve_hover(self.game, self._hover_anchor_pos)
            except Exception:
                tip = None

            # If we have a new tip, see if we should show it.
            if tip:
                required = int(tip.get('delay_ms', TOOLTIP_DELAY_MS))
                if elapsed >= required:
                    self._current_tooltip = tip
                    self._cached_tip = tip.copy()
                    self._cached_target_rect = tip.get('target')
                # If a tooltip is already showing, and it's the same one, keep it.
                elif self._current_tooltip and self._current_tooltip.get('id') == tip.get('id'):
                    pass
                else:
                    # Not time yet, and not showing this tip.
                    if not self._current_tooltip:
                         self._current_tooltip = None

            # If we don't have a new tip, maybe we can use the cached one.
            elif self._cached_tip and self._cached_target_rect:
                expanded = self._cached_target_rect.inflate(self._target_margin*2, self._target_margin*2)
                if expanded.collidepoint(*self._last_mouse_pos):
                    # We are still inside the old tooltip's area, keep it alive.
                    self._current_tooltip = self._cached_tip
                else:
                    # We have moved out of the cached tooltip area.
                    self._current_tooltip = None
                    self._cached_tip = None
                    self._cached_target_rect = None
            else:
                # No new tip, and no cached tip to fall back on.
                self._current_tooltip = None

        except Exception:
            TOOLTIP_BG_COLOR = (20,30,40)
            TOOLTIP_BORDER_COLOR = (140,180,210)
            WIDTH = surface.get_width(); HEIGHT = surface.get_height()
        
        # Game draw (without internal tooltip logic now)
        self.game.draw()
        
        # Overlay tooltip panel if present
        if self._current_tooltip:
            try:
                tip = self._current_tooltip
                title = tip.get('title','')
                lines = tip.get('lines',[])
                font = self.game.small_font if hasattr(self.game,'small_font') else self.game.font
                title_surf = font.render(title, True, (230,235,240))
                line_surfs = [font.render(ln, True, (230,235,240)) for ln in lines]
                pad = 8; line_spacing = 2
                max_w = max([title_surf.get_width()] + [s.get_width() for s in line_surfs]) if title_surf.get_width() or any(s.get_width() for s in line_surfs) else 0
                total_h = title_surf.get_height() + (4 if line_surfs else 0) + sum(s.get_height() + line_spacing for s in line_surfs)
                w = max_w + pad*2; h = total_h + pad*2
                mx,my = self._hover_anchor_pos
                x = mx + 16; y = my + 16
                if x + w > WIDTH - 4: x = WIDTH - w - 4
                if y + h > HEIGHT - 4: y = HEIGHT - h - 4
                panel = _pg.Surface((w, h), _pg.SRCALPHA)
                panel.fill((*TOOLTIP_BG_COLOR, 230) if len(TOOLTIP_BG_COLOR)==3 else TOOLTIP_BG_COLOR)
                _pg.draw.rect(panel, TOOLTIP_BORDER_COLOR, panel.get_rect(), width=1, border_radius=6)
                panel.blit(title_surf, (pad, pad))
                cy = pad + title_surf.get_height() + 4
                for s in line_surfs:
                    panel.blit(s, (pad, cy)); cy += s.get_height() + line_spacing
                surface.blit(panel, (x,y))
            except Exception:
                pass
    # is_done / next_screen inherited (always False unless externally finished)
