import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer

class RelicPanelSprite(BaseSprite):
    def __init__(self, panel, game, *groups):
        super().__init__(Layer.UI, panel, *groups)
        self.panel = panel
        self.game = game
        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sync_from_logical()

    def sync_from_logical(self):
        g = self.game
        panel = self.panel
        # Hide during shop or if no relic manager
        if not g or getattr(g, 'relic_manager', None) is None or getattr(g.relic_manager, 'shop_open', False):
            self.image.fill((0,0,0,0))
            self.dirty = 1
            return
        rm = getattr(g, 'relic_manager', None)
        relics = list(getattr(rm, 'active_relics', [])) if rm else []
        if not relics:
            self.image.fill((0,0,0,0))
            self.dirty = 1
            return
        # Create a separate rectangle for each relic
        from farkle.ui.settings import WIDTH, HEIGHT
        small_font = g.small_font
        rpad = 6
        v_spacing = 8  # Vertical space between relic items

        relic_surfs = []
        max_w = 0
        for r in relics:
            line_surf = small_font.render(r.name, True, (225, 230, 235))
            relic_surfs.append(line_surf)
            if line_surf.get_width() > max_w:
                max_w = line_surf.get_width()

        item_width = max_w + rpad * 2
        item_height = small_font.get_height() + rpad * 2
        
        total_width = item_width
        total_height = (item_height * len(relics)) + (v_spacing * max(0, len(relics) - 1))

        # Position to the right of dice and buttons
        dice_and_buttons_right = 0
        try:
            # Find rightmost die
            if g.dice:
                max_die_right = max(d.rect().right for d in g.dice)
                dice_and_buttons_right = max(dice_and_buttons_right, max_die_right)

            # Find rightmost button
            if g.ui_buttons:
                st = g.state_manager.get_state()
                visible_buttons = [b for b in g.ui_buttons if hasattr(b, 'visible_states') and st in b.visible_states]
                if visible_buttons:
                    max_button_right = max(b.rect.right for b in visible_buttons)
                    dice_and_buttons_right = max(dice_and_buttons_right, max_button_right)
        except Exception:
            dice_and_buttons_right = WIDTH * 0.75

        x = dice_and_buttons_right + 20 # 20px padding
        
        # Center it vertically relative to the action buttons area
        y = HEIGHT - 150 - (total_height / 2)

        # Clamp to screen edges
        if x + total_width > WIDTH - 12:
            x = WIDTH - total_width - 12
        if y < 0:
            y = 12
        if y + total_height > HEIGHT - 12:
            y = HEIGHT - total_height - 12

        self.image = pygame.Surface((total_width, total_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x,y))

        self.panel.relic_items = []
        current_y = 0
        for i, rs in enumerate(relic_surfs):
            relic = relics[i]
            # Create a surface for this individual relic item
            item_surf = pygame.Surface((item_width, item_height), pygame.SRCALPHA)
            
            # Draw background and border for the item
            pygame.draw.rect(item_surf, (30,45,58), item_surf.get_rect(), border_radius=6)
            pygame.draw.rect(item_surf, (95,140,175), item_surf.get_rect(), width=1, border_radius=6)
            
            # Blit the text onto the item surface
            text_x = (item_width - rs.get_width()) // 2
            text_y = (item_height - rs.get_height()) // 2
            item_surf.blit(rs, (text_x, text_y))
            
            # Blit the item surface onto the main panel surface
            self.image.blit(item_surf, (0, current_y))

            # Store the relic and its absolute rect for hover detection
            item_rect = pygame.Rect(x, y + current_y, item_width, item_height)
            self.panel.relic_items.append((relic, item_rect))
            
            current_y += item_height + v_spacing
            
        panel._last_rect = self.rect
        self.dirty = 1

__all__ = ["RelicPanelSprite"]
