import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer

class UIButtonSprite(BaseSprite):
    """Sprite wrapper for logical UIButton.

    Keeps rendering identical to UIButton.draw_with_game while enabling layered sprite pipeline.
    """
    def __init__(self, button, game, *groups):
        super().__init__(Layer.UI, button, *groups)
        self.button = button
        self.game = game
        # Pre-allocate surface at button size; resized if rect changes
        self.image = pygame.Surface((button.rect.width, button.rect.height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(button.rect.x, button.rect.y))
        self._last_rect_size = (button.rect.width, button.rect.height)
        # Constructor debug print removed.
        # Consolidated visibility: BaseSprite.update will hide when state not in visible_states.
        self.visible_states = getattr(button, 'visible_states', None)
        # Link logical button to sprite for test introspection.
        try:
            setattr(button, 'sprite', self)
        except Exception:
            pass
        # Initial gating for tests before first update cycle.
        try:
            st = game.state_manager.get_state()
            if self.visible_states is not None and st not in self.visible_states:
                self.image = pygame.Surface((1,1), pygame.SRCALPHA)
                self.rect = self.image.get_rect(topleft=(-1000,-1000))
        except Exception:
            pass
        self.sync_from_logical()

    def sync_from_logical(self):
        btn = self.button
        g = self.game
        # Ensure surface matches logical rect size even after being hidden (hidden sets image to 1x1 without updating _last_rect_size)
        if (btn.rect.width, btn.rect.height) != self._last_rect_size or self.image.get_width() != btn.rect.width or self.image.get_height() != btn.rect.height:
            self.image = pygame.Surface((btn.rect.width, btn.rect.height), pygame.SRCALPHA)
            self.rect = self.image.get_rect(topleft=(btn.rect.x, btn.rect.y))
            self._last_rect_size = (btn.rect.width, btn.rect.height)
        else:
            # Normal path: only move sprite
            self.rect.topleft = (btn.rect.x, btn.rect.y)
        # Clear
        self.image.fill((0,0,0,0))
        enabled = btn.is_enabled_fn(g)
        base_color = btn.base_color
        color = base_color if enabled else tuple(int(c * 0.7) for c in base_color)
        pygame.draw.rect(self.image, color, self.image.get_rect(), border_radius=btn.border_radius)
        outline_color = None
        if btn.name == 'reroll':
            abm = getattr(g, 'ability_manager', None)
            if abm and abm.selecting_ability() and abm.selecting_ability().id == 'reroll':
                outline_color = (255,255,255)
        elif enabled:
            outline_color = (240,240,240)
        if outline_color:
            pygame.draw.rect(self.image, outline_color, self.image.get_rect(), width=2, border_radius=btn.border_radius)
        lbl = btn.label_fn(g) if btn.label_fn else btn.label
        font = g.font
        # Adjust font size to fit button width if necessary
        max_width = self.image.get_width() - 10  # 5px padding on each side
        
        # Start with the default font
        current_font = font
        
        # Check if the text fits, and if not, reduce font size
        while current_font.size(lbl)[0] > max_width and current_font.get_height() > 10:
            # Create a new font object with a smaller size
            new_size = current_font.get_height() - 1
            current_font = pygame.font.Font(None, new_size)

        surf = current_font.render(lbl, True, (0,0,0))
        self.image.blit(surf, (self.image.get_width()//2 - surf.get_width()//2, self.image.get_height()//2 - surf.get_height()//2))
        self.dirty = 1

__all__ = ["UIButtonSprite"]
