import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer

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
        pygame.draw.circle(self.image, (60,90,120), (self.rect.width//2, self.rect.height//2), self.rect.width//2)
        pygame.draw.circle(self.image, (140,190,230), (self.rect.width//2, self.rect.height//2), self.rect.width//2, width=2)
        qsurf = self.game.font.render('?', True, (255,255,255))
        self.image.blit(qsurf, (self.rect.width//2 - qsurf.get_width()//2, self.rect.height//2 - qsurf.get_height()//2))
        self.dirty = 1


class RulesOverlaySprite(BaseSprite):
    def __init__(self, rules_overlay, game, *groups):
        super().__init__(Layer.OVERLAY, rules_overlay, *groups)
        self.rules_overlay = rules_overlay
        self.game = game
        from farkle.ui.settings import WIDTH, HEIGHT
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
        from farkle.ui.settings import WIDTH, HEIGHT
        self.image.fill((0,0,0,0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.image.blit(overlay, (0,0))
        panel_w, panel_h = 660, 440
        panel_rect = pygame.Rect(20, HEIGHT - panel_h - 40, panel_w, panel_h)
        pygame.draw.rect(self.image, (40,55,70), panel_rect, border_radius=10)
        pygame.draw.rect(self.image, (90,140,180), panel_rect, width=2, border_radius=10)
        title = g.font.render("Scoring Rules", True, (240,240,240))
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
            surf = small_font.render(ln, True, (230,230,235))
            self.image.blit(surf, (x, y))
        hint = small_font.render("Click ? to close", True, (190,200,210))
        self.image.blit(hint, (panel_rect.x + 20, panel_rect.bottom - 28))
        self.dirty = 1

# ShopOverlaySprite deprecated - shop now uses ChoiceWindow system
# Kept here temporarily for reference during migration
"""
class ShopOverlaySprite(BaseSprite):
    def __init__(self, shop_overlay, game, *groups):
        # Use MODAL layer so it draws above other overlays/UI elements.
        super().__init__(Layer.MODAL, shop_overlay, *groups)
        self.shop_overlay = shop_overlay
        self.game = game
        from farkle.ui.settings import WIDTH, HEIGHT
        self.image = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(0,0))
        self._offer_sprites = []
        # Visible only when shop_open flag true
        self.visible_predicate = lambda g: getattr(g.relic_manager, 'shop_open', False)
        self.sync_from_logical()

    def sync_from_logical(self):
        g = self.game
        if not getattr(g.relic_manager, 'shop_open', False):
            self.image.fill((0,0,0,0))
            # Kill sprites when not visible
            for s in self._offer_sprites:
                s.kill()
            self._offer_sprites.clear()
            self.dirty = 1
            return
            
        from farkle.ui.settings import WIDTH, HEIGHT
        self.image.fill((0,0,0,0))
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # Opaque but tinted navy so background isn't flat black
        dim.fill((18,28,40,230))
        self.image.blit(dim, (0,0))

        # --- Dynamic Panel Sizing ---
        offer_card_w, offer_card_h = 200, 180
        num_offers = len(getattr(g.relic_manager, 'offers', []))
        spacing = 25
        panel_pad_x = 50 # Horizontal padding inside the panel
        panel_pad_y = 150 # Vertical padding for title, gold, and skip button
        
        content_w = num_offers * offer_card_w + max(0, num_offers - 1) * spacing
        pw = content_w + panel_pad_x
        ph = offer_card_h + panel_pad_y
        
        panel = pygame.Rect((WIDTH - pw)//2, (HEIGHT - ph)//2, pw, ph)
        # --- End Dynamic Sizing ---

        pygame.draw.rect(self.image, (50,70,95), panel, border_radius=12)
        pygame.draw.rect(self.image, (120,170,210), panel, width=2, border_radius=12)
        
        offers = getattr(g.relic_manager, 'offers', [])
        self._ensure_offer_sprites(offers, panel)

        # --- Click Area Calculation ---
        btn_h = 32
        self._purchase_rects = []
        offer_area_top = panel.y + 80 # Y position for the top of the offer cards

        for idx, offer in enumerate(offers):
            # This calculation MUST match the positioning in _ensure_offer_sprites
            col_x = panel.x + (panel_pad_x // 2) + idx * (offer_card_w + spacing)
            box_rect = pygame.Rect(col_x, offer_area_top, offer_card_w, offer_card_h)
            
            # This rect MUST match the button's position inside ShopOfferSprite
            btn_rect = pygame.Rect(box_rect.x + 10, box_rect.bottom - btn_h - 10, box_rect.width - 20, btn_h)
            can_afford = g.player.gold >= offer.cost
            self._purchase_rects.append((idx, btn_rect, can_afford))

        self._skip_rect = pygame.Rect(panel.centerx - 80, panel.bottom - 50, 160, 40)
        pygame.draw.rect(self.image, (180,80,60), self._skip_rect, border_radius=8)
        stxt = g.font.render("Skip", True, (0,0,0))
        self.image.blit(stxt, (self._skip_rect.centerx - stxt.get_width()//2, self._skip_rect.centery - stxt.get_height()//2))
        self.dirty = 1

    def _ensure_offer_sprites(self, offers, panel_rect):
        g = self.game
        # Kill and clear existing sprites
        for s in self._offer_sprites:
            s.kill()
        self._offer_sprites.clear()

        offer_card_w, offer_card_h = 200, 180
        spacing = 25
        panel_pad_x = 50
        offer_area_top = panel_rect.y + 80

        from farkle.ui.sprites.shop_offer_sprite import ShopOfferSprite
        for idx, offer in enumerate(offers):
            col_x = panel_rect.x + (panel_pad_x // 2) + idx * (offer_card_w + spacing)
            sprite = ShopOfferSprite(offer, g, self.groups())
            sprite.rect.topleft = (col_x, offer_area_top)
            self._offer_sprites.append(sprite)

    def handle_click(self, game, pos) -> bool:  # type: ignore[override]
        if not getattr(game.relic_manager, 'shop_open', False):
            return False
        mx,my = pos
        for idx, rect, can_afford in getattr(self, '_purchase_rects', []):
            if rect.collidepoint(mx,my) and can_afford:
                from farkle.core.game_event import GameEvent, GameEventType
                game.event_listener.publish(GameEvent(GameEventType.REQUEST_BUY_RELIC, payload={"offer_index": idx}))
                return True
        skip_rect = getattr(self, '_skip_rect', None)
        if skip_rect and skip_rect.collidepoint(mx,my):
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP))
            return True
        return True  # Swallow clicks while open
"""

__all__ = ["HelpIconSprite", "RulesOverlaySprite"]
