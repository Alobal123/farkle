import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer

class PlayerHUDSprite(BaseSprite):
    def __init__(self, player, game, *groups):
        super().__init__(Layer.UI, player, *groups)
        self.player = player
        self.game = game
        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sync_from_logical()

    def sync_from_logical(self):
        g = self.game
        p = self.player
        if not g:
            return
        # Previously hidden during SHOP; requirement change: keep HUD visible while shopping.
        # (If SHOP state is later removed entirely this block can be deleted.)
        try:
            if g.state_manager.get_state().name == 'SHOP':
                # Fall through (no early return) to render normally.
                pass
        except Exception:
            pass
        hud_padding = 10
        hud_lines = [
            f"Turns: {g.level_state.turns_left}",
            f"Gold: {p.gold}",
            f"Faith: {p.faith}",
            f"Income: {p.temple_income}",
        ]
        line_surfs = []
        for t in hud_lines:
            color = (250,250,250)
            line_surfs.append(g.small_font.render(t, True, color))
        from farkle.ui.settings import WIDTH
        width_needed = max(s.get_width() for s in line_surfs) + hud_padding * 2
        height_needed = sum(s.get_height() for s in line_surfs) + hud_padding * 2 + 6
        self.image = pygame.Surface((width_needed, height_needed), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(WIDTH - width_needed - 20, 20))
        pygame.draw.rect(self.image, (40,55,70), self.image.get_rect(), border_radius=8)
        pygame.draw.rect(self.image, (90,140,180), self.image.get_rect(), width=2, border_radius=8)
        y = hud_padding
        for s in line_surfs:
            self.image.blit(s, (hud_padding, y))
            y += s.get_height() + 2
        self.dirty = 1

class GodsPanelSprite(BaseSprite):
    def __init__(self, gods_manager, game, *groups):
        super().__init__(Layer.UI, gods_manager, *groups)
        self.gods_manager = gods_manager
        self.game = game
        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sync_from_logical()

    def sync_from_logical(self):
        gm = self.gods_manager
        g = self.game
        if not g or not gm.worshipped:
            # Clear
            self.image.fill((0,0,0,0))
            self.dirty = 1
            return
        # Requirement update: Gods panel should be covered by the shop (hidden) while SHOP is active.
        try:
            if g.state_manager.get_state().name == 'SHOP':
                self.image.fill((0,0,0,0))
                self.rect.topleft = (-1000,-1000)
                self.dirty = 1
                return
        except Exception:
            pass
        
        from farkle.ui.settings import WIDTH, HEIGHT
        y_start = 20
        
        font = g.font
        small_font = getattr(g, 'small_font', font)
        
        # Compute needed width incrementally
        name_surfs = []
        max_name_h = 0
        for i, god in enumerate(gm.worshipped):
            base_display = f"{god.name} Lv{god.level}"
            display = f"[{base_display}]" if i == gm.active_index else base_display
            try:
                surf = font.render(display, True, (240,230,140) if i == gm.active_index else (180,210,250))
            except Exception:
                surf = font.render("?", True, (200,200,200))
            name_surfs.append(surf)
            max_name_h = max(max_name_h, surf.get_height())
        # xp text height
        xp_h = small_font.get_height()
        bar_h = 6
        panel_h = max_name_h + 2 + xp_h + 2 + bar_h
        # Compute width
        spacing = 12
        total_width = 0
        per_god_rects = []
        for surf in name_surfs:
            total_width += surf.get_width() + spacing
        if name_surfs:
            total_width -= spacing  # last spacing not needed
        
        x_start = (WIDTH - total_width) // 2

        # Build surface
        self.image = pygame.Surface((total_width, panel_h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x_start, y_start))
        # Draw label
        
        x = 0
        xp_req_cache = []
        for i, (surf, god) in enumerate(zip(name_surfs, gm.worshipped)):
            rect = surf.get_rect(topleft=(x,0))
            god._rect = pygame.Rect(self.rect.x + rect.x, self.rect.y + rect.y, rect.width, rect.height)
            god._active = (i == gm.active_index)
            self.image.blit(surf, rect.topleft)
            # XP text
            xp_req = god.xp_required_for_next()
            xp_req_cache.append(xp_req)
            if xp_req > 0:
                xp_text = f"XP {god.xp}/{xp_req}"
            else:
                xp_text = "MAX"
            xp_surf = small_font.render(xp_text, True, (200,210,220))
            xp_pos = (rect.x, rect.bottom + 2)
            self.image.blit(xp_surf, xp_pos)
            # XP bar
            bar_x = rect.x
            bar_y = xp_pos[1] + xp_surf.get_height() + 2
            bar_w = max(80, min(160, surf.get_width()))
            pygame.draw.rect(self.image, (50,60,70), pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=3)
            pygame.draw.rect(self.image, (90,110,130), pygame.Rect(bar_x, bar_y, bar_w, bar_h), width=1, border_radius=3)
            if xp_req > 0:
                pct = max(0.0, min(1.0, god.xp / float(xp_req)))
            else:
                pct = 1.0
            fill_w = int(bar_w * pct)
            if fill_w > 0:
                fill_color = (240,230,140) if xp_req == 0 else (90,200,110)
                pygame.draw.rect(self.image, fill_color, pygame.Rect(bar_x, bar_y, fill_w, bar_h), border_radius=3)
            x += rect.width + spacing
        self.dirty = 1

__all__ = ["PlayerHUDSprite", "GodsPanelSprite"]
