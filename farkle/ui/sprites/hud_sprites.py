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
        
        # Compute needed width incrementally - only god name + level now
        name_surfs = []
        max_name_h = 0
        for i, god in enumerate(gm.worshipped):
            base_display = f"{god.name} Lv{god.level}"
            try:
                surf = font.render(base_display, True, (180,210,250))
            except Exception:
                surf = font.render("?", True, (200,200,200))
            name_surfs.append(surf)
            max_name_h = max(max_name_h, surf.get_height())
        
        # Panel height is just the name height now (no XP bar)
        panel_h = max_name_h + 4
        
        # Compute width
        spacing = 12
        total_width = 0
        for surf in name_surfs:
            total_width += surf.get_width() + spacing
        if name_surfs:
            total_width -= spacing  # last spacing not needed
        
        x_start = (WIDTH - total_width) // 2

        # Build surface
        self.image = pygame.Surface((total_width, panel_h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x_start, y_start))
        
        # Draw gods
        x = 0
        for i, (surf, god) in enumerate(zip(name_surfs, gm.worshipped)):
            rect = surf.get_rect(topleft=(x, 2))
            god._rect = pygame.Rect(self.rect.x + rect.x, self.rect.y + rect.y, rect.width, rect.height)
            self.image.blit(surf, rect.topleft)
            x += rect.width + spacing
        self.dirty = 1

__all__ = ["PlayerHUDSprite", "GodsPanelSprite"]
