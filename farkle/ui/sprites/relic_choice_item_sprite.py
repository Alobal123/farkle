"""Sprite for displaying relics in choice window."""

import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer
from farkle.ui.choice_window import ChoiceWindowState


class RelicChoiceItemSprite(BaseSprite):
    """Displays a single relic option in the choice window.
    
    Shows relic name, cost, effect text, and purchase button.
    Visual highlight when selected similar to god cards.
    """
    
    def __init__(self, logical_item, choice_window, game, *groups):
        # Use TOOLTIP layer so items appear above the choice window overlay
        super().__init__(Layer.TOOLTIP, logical_item, *groups)
        self.logical_item = logical_item
        self.choice_window = choice_window
        self.game = game
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        
        # Only visible when choice window is maximized
        self.visible_predicate = lambda g: (
            choice_window.is_open() and 
            choice_window.state == ChoiceWindowState.MAXIMIZED
        )
        
        self.sync_from_logical()
    
    def sync_from_logical(self):
        """Render the relic card with cost, effect text, and selection highlight."""
        g = self.game
        item = self.logical_item
        offer = item.payload  # ShopOffer object
        
        # Card dimensions
        card_width = 220
        card_height = 200
        
        self.image = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
        box_rect = self.image.get_rect()
        
        # Check if this item is selected
        selected = item.id in [self.choice_window.items[i].id for i in self.choice_window.selected_indices]
        
        # Visual highlight for selected card
        if selected:
            # Outer glow
            glow_rect = box_rect.inflate(8, 8)
            pygame.draw.rect(self.image, (100, 150, 255), glow_rect, border_radius=10)
            pygame.draw.rect(self.image, (120, 180, 255), glow_rect, width=3, border_radius=10)
            
            bg_color = (85, 110, 150)  # Brighter background
            border_color = (180, 220, 255)  # Much brighter border
            border_width = 4
        else:
            bg_color = (65, 90, 120)
            border_color = (120, 170, 210)
            border_width = 2
        
        # Main card background and border
        pygame.draw.rect(self.image, bg_color, box_rect, border_radius=8)
        pygame.draw.rect(self.image, border_color, box_rect, width=border_width, border_radius=8)
        
        y = 12
        
        # Relic name
        name_surf = g.font.render(offer.name, True, (255, 255, 255))
        self.image.blit(name_surf, (10, y))
        y += name_surf.get_height() + 8
        
        # Cost
        can_afford = g.player.gold >= offer.cost
        cost_color = (230, 210, 100) if can_afford else (180, 100, 100)
        cost_surf = g.small_font.render(f"Cost: {offer.cost}g", True, cost_color)
        self.image.blit(cost_surf, (10, y))
        y += cost_surf.get_height() + 8
        
        # Effect text with wrapping
        if offer.effect_text:
            effect_color = (210, 210, 210)
            line_spacing = g.small_font.get_linesize()
            max_width = card_width - 20
            
            words = offer.effect_text.split(' ')
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if g.small_font.size(test_line)[0] < max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word + " "
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                if y + line_spacing > box_rect.bottom - 10:
                    break
                line_surf = g.small_font.render(line.strip(), True, effect_color)
                self.image.blit(line_surf, (10, y))
                y += line_spacing
        
        self.dirty = 1
    
    def get_tooltip_lines(self) -> list[str]:
        """Return tooltip text for this relic."""
        offer = self.logical_item.payload
        relic = offer.payload  # The actual Relic object
        
        lines = []
        if hasattr(relic, 'description') and relic.description:
            lines.append(relic.description)
        
        lines.append("")  # Blank line
        lines.append(f"Cost: {offer.cost} gold")
        
        player_gold = self.game.player.gold
        if player_gold < offer.cost:
            lines.append(f"You have: {player_gold}g (not enough)")
        else:
            lines.append(f"You have: {player_gold}g")
        
        return lines


__all__ = ["RelicChoiceItemSprite"]
