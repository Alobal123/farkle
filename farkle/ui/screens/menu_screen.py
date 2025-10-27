"""Main menu screen for Farkle game."""
import pygame
from .base_screen import SimpleScreen
from farkle.ui.settings import WIDTH, HEIGHT, BG_COLOR, TEXT_PRIMARY


class MenuScreen(SimpleScreen):
    """Main menu screen with New Game button.
    
    When New Game is clicked, signals transition to game screen.
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        super().__init__()
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.SysFont("Arial", 72, bold=True)
        self.button_font = pygame.font.SysFont("Arial", 36)
        
        # Button dimensions
        button_width = 300
        button_height = 80
        button_spacing = 20
        
        # New Game button
        button_x = WIDTH // 2 - button_width // 2
        button_y = HEIGHT // 2 + 20
        self.new_game_button = pygame.Rect(button_x, button_y, button_width, button_height)
        
        # Statistics button (below New Game)
        stats_button_y = button_y + button_height + button_spacing
        self.stats_button = pygame.Rect(button_x, stats_button_y, button_width, button_height)
        
        # Button colors
        self.new_game_color = (60, 120, 80)
        self.new_game_hover_color = (80, 160, 110)
        self.stats_color = (60, 80, 120)
        self.stats_hover_color = (80, 110, 160)
        self.button_text_color = (255, 255, 255)
        
        # Track hover state
        self.hovering_new_game = False
        self.hovering_stats = False
        
    def handle_event(self, event: pygame.event.Event) -> None:  # type: ignore[override]
        if event.type == pygame.MOUSEMOTION:
            self.hovering_new_game = self.new_game_button.collidepoint(event.pos)
            self.hovering_stats = self.stats_button.collidepoint(event.pos)
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.new_game_button.collidepoint(event.pos):
                    # Signal transition to game screen
                    self.finish(next_screen='game')
                elif self.stats_button.collidepoint(event.pos):
                    # Signal transition to statistics screen
                    self.finish(next_screen='statistics')
    
    def update(self, dt: float) -> None:  # type: ignore[override]
        pass
    
    def draw(self, surface: pygame.Surface) -> None:  # type: ignore[override]
        # Clear background
        surface.fill(BG_COLOR)
        
        # Draw title
        title_text = "GOD FARKLE"
        title_surf = self.title_font.render(title_text, True, TEXT_PRIMARY)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        surface.blit(title_surf, title_rect)
        
        # Draw subtitle/flavor text
        subtitle_text = "Roll the Dice, Tempt the Fates"
        subtitle_surf = self.font.render(subtitle_text, True, (180, 180, 200))
        subtitle_rect = subtitle_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 60))
        surface.blit(subtitle_surf, subtitle_rect)
        
        # Draw New Game button
        new_game_color = self.new_game_hover_color if self.hovering_new_game else self.new_game_color
        pygame.draw.rect(surface, new_game_color, self.new_game_button, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), self.new_game_button, width=2, border_radius=8)
        
        # Draw New Game button text
        button_text = "New Game"
        button_text_surf = self.button_font.render(button_text, True, self.button_text_color)
        button_text_rect = button_text_surf.get_rect(center=self.new_game_button.center)
        surface.blit(button_text_surf, button_text_rect)
        
        # Draw Statistics button
        stats_color = self.stats_hover_color if self.hovering_stats else self.stats_color
        pygame.draw.rect(surface, stats_color, self.stats_button, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), self.stats_button, width=2, border_radius=8)
        
        # Draw Statistics button text
        stats_text = "Statistics"
        stats_text_surf = self.button_font.render(stats_text, True, self.button_text_color)
        stats_text_rect = stats_text_surf.get_rect(center=self.stats_button.center)
        surface.blit(stats_text_surf, stats_text_rect)
