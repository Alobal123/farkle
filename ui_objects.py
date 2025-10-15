from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Callable, Optional, Any
from game_object import GameObject
from game_event import GameEvent, GameEventType
from typing import Callable, Optional, Any
from settings import (
    BTN_ROLL_COLOR, BTN_LOCK_COLOR_DISABLED, BTN_LOCK_COLOR_ENABLED, BTN_BANK_COLOR,
    ROLL_BTN, LOCK_BTN, BANK_BTN, NEXT_BTN, REROLL_BTN
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
        self.rect = rect
        self.label = label
        self.base_color = base_color
        self.disabled_color = disabled_color
        self.event_type = event_type
        self.is_enabled_fn = is_enabled_fn
        self.label_fn = label_fn

    def draw(self, surface: pygame.Surface) -> None:
        game = getattr(surface, 'game_ref', None)  # not reliable; renderer will pass game separately if needed
        # We rely on a global context (pygame display) so draw method kept simple; actual enabling resolved at click time
        raise NotImplementedError("UIButton.draw requires game context; use draw_with_game(game, surface)")

    def draw_with_game(self, game, surface: pygame.Surface):
        enabled = self.is_enabled_fn(game)
        color = self.base_color if enabled else tuple(max(0,int(c*0.45)) for c in self.base_color)
        pygame.draw.rect(surface, color, self.rect, border_radius=self.border_radius)
        # Outline when active/selected (e.g. ability selecting)
        outline = None
        if self.name == 'reroll':
            abm = getattr(game, 'ability_manager', None)
            if abm and abm.selecting_ability() and abm.selecting_ability().id == 'reroll':
                outline = (255,255,255)
        if outline:
            pygame.draw.rect(surface, outline, self.rect, width=2, border_radius=self.border_radius)
        lbl = self.label_fn(game) if self.label_fn else self.label
        txt_color = (0,0,0) if enabled else (60,60,60)
        surf = game.font.render(lbl, True, txt_color)
        surface.blit(surf, (self.rect.x + (self.rect.width - surf.get_width())//2, self.rect.y + (self.rect.height - surf.get_height())//2))

    def handle_click(self, game, pos) -> bool:  # pass game explicitly
        if not self.rect.collidepoint(*pos):
            return False
        if not self.is_enabled_fn(game):
            return True
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
    def lock_enabled(g):
        st = g.state_manager.get_state()
        return st in (g.state_manager.state.PRE_ROLL, g.state_manager.state.ROLLING) and g.selection_is_single_combo() and g.any_scoring_selection()
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
        st = g.state_manager.get_state()
        return st in (g.state_manager.state.FARKLE, g.state_manager.state.BANKED)
    buttons = [
        UIButton('reroll', REROLL_BTN, 'REROLL', (120,160,200), (120,160,200), None, reroll_enabled, reroll_label),
        UIButton('roll', ROLL_BTN, 'ROLL', BTN_ROLL_COLOR, BTN_ROLL_COLOR, GameEventType.REQUEST_ROLL, roll_enabled),
        UIButton('lock', LOCK_BTN, 'LOCK', BTN_LOCK_COLOR_ENABLED, BTN_LOCK_COLOR_DISABLED, GameEventType.REQUEST_LOCK, lock_enabled),
        UIButton('bank', BANK_BTN, 'BANK', BTN_BANK_COLOR, BTN_BANK_COLOR, GameEventType.REQUEST_BANK, bank_enabled),
        UIButton('next', NEXT_BTN, 'Next Turn', (200,50,50), (200,50,50), GameEventType.REQUEST_NEXT_TURN, next_enabled),
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

    def draw(self, surface):  # type: ignore[override]
        import pygame
        if not hasattr(self, 'game') or not self.game:  # type: ignore[attr-defined]
            return
        # Simple circle with '?' inside
        pygame.draw.circle(surface, (60,90,120), self.rect.center, self.rect.width//2)
        pygame.draw.circle(surface, (140,190,230), self.rect.center, self.rect.width//2, width=2)
        qsurf = self.game.font.render('?', True, (255,255,255))  # type: ignore[attr-defined]
        surface.blit(qsurf, (self.rect.centerx - qsurf.get_width()//2, self.rect.centery - qsurf.get_height()//2))

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

    def draw(self, surface):  # type: ignore[override]
        if not self.game:  # type: ignore[attr-defined]
            return
        g = self.game  # type: ignore[attr-defined]
        if getattr(g, 'relic_manager', None) is None or getattr(g.relic_manager, 'shop_open', False):
            return
        try:
            lines = g.renderer.get_active_relic_debug_lines()  # reuse existing helper for now
        except Exception:
            lines = ["Relics: (error)"]
        if not lines:
            return
        import pygame
        small_font = g.small_font
        rpad = 6
        r_line_surfs = [small_font.render(ln, True, (220,220,230)) for ln in lines]
        hud_width = 0
        # Try to locate player HUD area to anchor below it (Player HUD currently drawn in Player.draw or renderer; placeholder x).
        # For now compute right edge based on WIDTH constant.
        from settings import WIDTH
        width = max(s.get_width() for s in r_line_surfs) + rpad*2
        height = sum(s.get_height() for s in r_line_surfs) + rpad*2 + 4
        # Position top-right under assumed HUD top margin (we mirror old layout).
        hud_top = 20
        hud_height_guess = 120
        rect = pygame.Rect(WIDTH - width - 20, hud_top + hud_height_guess + 8, width, height)
        pygame.draw.rect(surface, (35,50,62), rect, border_radius=6)
        pygame.draw.rect(surface, (80,120,155), rect, width=1, border_radius=6)
        y = rect.y + rpad
        for rs in r_line_surfs:
            surface.blit(rs, (rect.x + rpad, y))
            y += rs.get_height() + 2
        self._last_rect = rect
    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        # Non-interactive; return False so event propagates.
        return False

class ShopOverlay(GameObject):
    """Full-screen modal overlay for relic shop."""
    def __init__(self):
        super().__init__(name="ShopOverlay")
        self.purchase_rects: list = []
        self.skip_rect = None
        self.panel_rect = None
        self.dim_color = (0,0,0,180)
        self.panel_size = (600, 340)

    def draw(self, surface):  # type: ignore[override]
        if not self.game:  # type: ignore[attr-defined]
            return
        g = self.game  # type: ignore[attr-defined]
        if not getattr(g.relic_manager, 'shop_open', False):
            return
        import pygame
        from settings import WIDTH, HEIGHT
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(self.dim_color)
        surface.blit(overlay, (0,0))
        pw, ph = self.panel_size
        panel_rect = pygame.Rect((WIDTH - pw)//2, (HEIGHT - ph)//2, pw, ph)
        self.panel_rect = panel_rect
        pygame.draw.rect(surface, (50,70,95), panel_rect, border_radius=12)
        pygame.draw.rect(surface, (120,170,210), panel_rect, width=2, border_radius=12)
        font = g.font
        title_surf = font.render("Shop", True, (250,250,250))
        surface.blit(title_surf, (panel_rect.x + 20, panel_rect.y + 16))
        gold_surf = font.render(f"Your Gold: {g.player.gold}", True, (230,230,230))
        surface.blit(gold_surf, (panel_rect.x + 20, panel_rect.y + 16 + title_surf.get_height() + 6))
        offers = getattr(g.relic_manager, 'offers', [])
        offer_area_top = panel_rect.y + 90
        offer_width = (panel_rect.width - 80) // 3
        offer_height = panel_rect.height - 150
        self.purchase_rects = []
        from score_modifiers import FlatRuleBonus
        for idx, offer in enumerate(offers):
            col_x = panel_rect.x + 20 + idx * (offer_width + 20)
            box_rect = pygame.Rect(col_x, offer_area_top, offer_width, offer_height)
            pygame.draw.rect(surface, (65,90,120), box_rect, border_radius=8)
            pygame.draw.rect(surface, (120,170,210), box_rect, width=2, border_radius=8)
            y = box_rect.y + 12
            name_surf = font.render(offer.relic.name, True, (255,255,255))
            surface.blit(name_surf, (box_rect.x + 10, y)); y += name_surf.get_height() + 6
            # Global multipliers removed; do not display multiplier lines
            for m in offer.relic.modifier_chain.snapshot():
                if isinstance(m, FlatRuleBonus):
                    fsurf = g.small_font.render(f"+{m.amount} {m.rule_key}", True, (255,200,140))
                    surface.blit(fsurf, (box_rect.x + 10, y)); y += fsurf.get_height() + 2
            csurf = g.small_font.render(f"Cost: {offer.cost}g", True, (210,210,210))
            surface.blit(csurf, (box_rect.x + 10, y)); y += csurf.get_height() + 8
            btn_h = 32
            btn_rect = pygame.Rect(box_rect.x + 10, box_rect.bottom - btn_h - 10, box_rect.width - 20, btn_h)
            can_afford = g.player.gold >= offer.cost
            pygame.draw.rect(surface, (80,200,110) if can_afford else (60,90,70), btn_rect, border_radius=6)
            ptxt = g.small_font.render("Purchase", True, (0,0,0) if can_afford else (120,120,120))
            surface.blit(ptxt, (btn_rect.centerx - ptxt.get_width()//2, btn_rect.centery - ptxt.get_height()//2))
            self.purchase_rects.append(btn_rect)
        skip_rect = pygame.Rect(panel_rect.centerx - 80, panel_rect.bottom - 50, 160, 40)
        pygame.draw.rect(surface, (180,80,60), skip_rect, border_radius=8)
        stxt = font.render("Skip", True, (0,0,0))
        surface.blit(stxt, (skip_rect.centerx - stxt.get_width()//2, skip_rect.centery - stxt.get_height()//2))
        self.skip_rect = skip_rect

    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        if not getattr(game.relic_manager, 'shop_open', False):
            return False
        mx,my = pos
        # If layout not yet drawn this frame, synthesize rects so early clicks still work
        if self.skip_rect is None or not self.purchase_rects:
            try:
                from settings import WIDTH, HEIGHT
                import pygame
                pw, ph = self.panel_size
                panel_rect = pygame.Rect((WIDTH - pw)//2, (HEIGHT - ph)//2, pw, ph)
                self.panel_rect = panel_rect
                # Construct skip_rect
                self.skip_rect = pygame.Rect(panel_rect.centerx - 80, panel_rect.bottom - 50, 160, 40)
                # Minimal purchase button rects (non-interactive until draw populates offers)
                if not self.purchase_rects:
                    self.purchase_rects = []
            except Exception:
                pass
        for idx, rect in enumerate(self.purchase_rects):
            if rect.collidepoint(mx,my):
                game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC, payload={"offer_index": idx}))
                return True
        if self.skip_rect and self.skip_rect.collidepoint(mx,my):
            game.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP))
            return True
        return False

class RulesOverlay(GameObject):
    """Help / rules panel shown when game.show_help True."""
    def __init__(self):
        super().__init__(name="RulesOverlay")

    def draw(self, surface):  # type: ignore[override]
        if not self.game:  # type: ignore[attr-defined]
            return
        g = self.game  # type: ignore[attr-defined]
        if not getattr(g, 'show_help', False):
            return
        import pygame
        from settings import WIDTH, HEIGHT
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        surface.blit(overlay, (0,0))
        panel_w, panel_h = 660, 440
        panel_rect = pygame.Rect(20, HEIGHT - panel_h - 40, panel_w, panel_h)
        pygame.draw.rect(surface, (40,55,70), panel_rect, border_radius=10)
        pygame.draw.rect(surface, (90,140,180), panel_rect, width=2, border_radius=10)
        title = g.font.render("Scoring Rules", True, (240,240,240))
        surface.blit(title, (panel_rect.x + 16, panel_rect.y + 16))
        by_key = {r.rule_key: r for r in g.rules.rules}
        lines: list[str] = []
        for key, label in [( 'Straight6', 'Straight 1-6'), ('Straight1to5','Straight 1-5'), ('Straight2to6','Straight 2-6')]:
            r = by_key.get(key)
            if r:
                pts = getattr(r, 'points', None)
                if pts:
                    lines.append(f"{label}: {pts}")
        for sv in ('1','5'):
            r = by_key.get(f'SingleValue:{sv}')
            if r:
                pts = getattr(r, 'points', None)
                if pts:
                    lines.append(f"Single {sv}s: {pts} each")
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
            line_parts = [f"{v}: 3-kind {base}"]
            if four: line_parts.append(f"4-kind {base*2}")
            if five: line_parts.append(f"5-kind {base*3}")
            if six: line_parts.append(f"6-kind {base*4}")
            lines.append("Of-a-Kind " + ", ".join(line_parts))
        small_font = g.small_font if hasattr(g, 'small_font') else g.font
        line_height = small_font.get_height() + 4
        max_rows = 14
        columns = 1 if len(lines) <= max_rows else 2
        col_width = (panel_rect.width - 40) // columns
        start_y = panel_rect.y + 60
        for idx, ln in enumerate(lines):
            col = idx // max_rows if columns > 1 else 0
            row = idx % max_rows if columns > 1 else idx
            if start_y + (row+1)*line_height > panel_rect.bottom - 40:
                break
            x = panel_rect.x + 20 + col * col_width
            y = start_y + row * line_height
            surf = small_font.render(ln, True, (230,230,235))
            surface.blit(surf, (x, y))
        hint = small_font.render("Click ? to close", True, (190,200,210))
        surface.blit(hint, (panel_rect.x + 20, panel_rect.bottom - 28))
    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        # Overlay currently closes via HelpIcon; ignore clicks.
        return False
