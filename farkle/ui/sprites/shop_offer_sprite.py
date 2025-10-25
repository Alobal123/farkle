import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer

class ShopOfferSprite(BaseSprite):
    def __init__(self, offer, game, *groups):
        super().__init__(Layer.MODAL, offer, *groups)
        self.offer = offer
        self.game = game
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sync_from_logical()

    def sync_from_logical(self):
        offer = self.offer
        g = self.game
        
        offer_width = 200
        offer_height = 180

        self.image = pygame.Surface((offer_width, offer_height), pygame.SRCALPHA)
        
        box_rect = self.image.get_rect()
        # Main box
        pygame.draw.rect(self.image, (65,90,120), box_rect, border_radius=8)
        pygame.draw.rect(self.image, (120,170,210), box_rect, width=1, border_radius=8)
        
        y = box_rect.y + 12
        
        # Offer Name
        name_surf = g.font.render(offer.name, True, (255,255,255))
        self.image.blit(name_surf, (box_rect.x + 10, y))
        y += name_surf.get_height() + 4

        # --- Calculate Footer Area ---
        btn_h = 32
        cost_h = g.small_font.render("Cost: 0g", True, (0,0,0)).get_height()
        footer_h = btn_h + cost_h + 20 # button + cost + padding
        footer_top_y = box_rect.height - footer_h

        # --- Effect Text (with wrapping and boundary) ---
        effect_font = g.small_font
        effect_text = offer.effect_text or "No effect description."
        effect_color = (210, 210, 210)
        
        line_spacing = effect_font.get_linesize()
        max_width = box_rect.width - 20 # 10px padding on each side
        
        words = effect_text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if effect_font.size(test_line)[0] < max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)

        effect_y = y
        for line in lines:
            # Ensure text does not draw over the footer area
            if effect_y + line_spacing > footer_top_y:
                break 
            line_surf = effect_font.render(line.strip(), True, effect_color)
            self.image.blit(line_surf, (box_rect.x + 10, effect_y))
            effect_y += line_spacing

        # --- Bottom-aligned elements ---
        
        # Purchase Button
        btn_rect = pygame.Rect(box_rect.x + 10, box_rect.bottom - btn_h - 10, box_rect.width - 20, btn_h)
        can_afford = g.player.gold >= offer.cost
        pygame.draw.rect(self.image, (80,200,110) if can_afford else (60,90,70), btn_rect, border_radius=6)
        ptxt = g.small_font.render("Purchase", True, (0,0,0) if can_afford else (120,120,120))
        self.image.blit(ptxt, (btn_rect.centerx - ptxt.get_width()//2, btn_rect.centery - ptxt.get_height()//2))

        # Cost (drawn above the button)
        cost_surf = g.small_font.render(f"Cost: {offer.cost}g", True, (230, 210, 100))
        cost_y = btn_rect.y - cost_surf.get_height() - 5 # 5px padding
        self.image.blit(cost_surf, (box_rect.x + 10, cost_y))

        self.dirty = 1
