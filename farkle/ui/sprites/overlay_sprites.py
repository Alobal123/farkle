import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer
from farkle.ui.settings import (
    HELP_ICON_BG, HELP_ICON_BORDER, TEXT_WHITE,
    PANEL_BG_DARK, PANEL_BORDER_LIGHT, TEXT_MEDIUM_LIGHT,
    TEXT_VERY_LIGHT, TEXT_INFO, WIDTH, HEIGHT
)

class HelpIconSprite(BaseSprite):
    def __init__(self, help_icon, game, *groups):
        super().__init__(Layer.UI, help_icon, *groups)
        self.help_icon = help_icon
        self.game = game
        self.image = pygame.Surface((help_icon.rect.width, help_icon.rect.height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(help_icon.rect.x, help_icon.rect.y))
        self.sync_from_logical()

    def sync_from_logical(self):
        hi = self.help_icon
        self.rect.topleft = (hi.rect.x, hi.rect.y)
        self.image.fill((0,0,0,0))
        pygame.draw.circle(self.image, HELP_ICON_BG, (self.rect.width//2, self.rect.height//2), self.rect.width//2)
        pygame.draw.circle(self.image, HELP_ICON_BORDER, (self.rect.width//2, self.rect.height//2), self.rect.width//2, width=2)
        qsurf = self.game.font.render('?', True, TEXT_WHITE)
        self.image.blit(qsurf, (self.rect.width//2 - qsurf.get_width()//2, self.rect.height//2 - qsurf.get_height()//2))
        self.dirty = 1


class RulesOverlaySprite(BaseSprite):
    def __init__(self, rules_overlay, game, *groups):
        super().__init__(Layer.OVERLAY, rules_overlay, *groups)
        self.rules_overlay = rules_overlay
        self.game = game
        self.image = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(0,0))
        self.sync_from_logical()

    def sync_from_logical(self):
        ro = self.rules_overlay
        g = self.game
        if not getattr(g, 'show_help', False):
            # Clear image to transparent
            self.image.fill((0,0,0,0))
            self.dirty = 1
            return
        self.image.fill((0,0,0,0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.image.blit(overlay, (0,0))
        panel_w, panel_h = 660, 440
        panel_rect = pygame.Rect(20, HEIGHT - panel_h - 40, panel_w, panel_h)
        pygame.draw.rect(self.image, PANEL_BG_DARK, panel_rect, border_radius=10)
        pygame.draw.rect(self.image, PANEL_BORDER_LIGHT, panel_rect, width=2, border_radius=10)
        title = g.font.render("Scoring Rules", True, TEXT_MEDIUM_LIGHT)
        self.image.blit(title, (panel_rect.x + 16, panel_rect.y + 16))
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
            surf = small_font.render(ln, True, TEXT_VERY_LIGHT)
            self.image.blit(surf, (x, y))
        hint = small_font.render("Click ? to close", True, TEXT_INFO)
        self.image.blit(hint, (panel_rect.x + 20, panel_rect.bottom - 28))
        self.dirty = 1

__all__ = ["HelpIconSprite", "RulesOverlaySprite"]
