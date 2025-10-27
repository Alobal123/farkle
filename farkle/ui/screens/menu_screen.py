"""Main menu screen for Farkle game."""
import pygame
from .base_screen import SimpleScreen
from farkle.ui.settings import WIDTH, HEIGHT, BG_COLOR, TEXT_PRIMARY


class MenuScreen(SimpleScreen):
    """Main menu screen with New Game button.
    
    When New Game is clicked, signals transition to game screen.
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, has_save: bool = False):
        super().__init__()
        self.screen = screen
        self.font = font
        self.has_save = has_save
        self.title_font = pygame.font.SysFont("Arial", 72, bold=True)
        self.button_font = pygame.font.SysFont("Arial", 36)
        
        # Button dimensions
        button_width = 300
        button_height = 80
        button_spacing = 20
        
        # Calculate button positions based on whether we have a save
        button_x = WIDTH // 2 - button_width // 2
        start_y = HEIGHT // 2 + 20
        
        # Continue button (only shown if has_save)
        if self.has_save:
            self.continue_button = pygame.Rect(button_x, start_y, button_width, button_height)
            new_game_y = start_y + button_height + button_spacing
        else:
            self.continue_button = None
            new_game_y = start_y
        
        # New Game button
        self.new_game_button = pygame.Rect(button_x, new_game_y, button_width, button_height)
        
        # Statistics button (below New Game)
        stats_button_y = new_game_y + button_height + button_spacing
        self.stats_button = pygame.Rect(button_x, stats_button_y, button_width, button_height)
        
        # Button colors
        self.continue_color = (80, 120, 60)
        self.continue_hover_color = (110, 160, 80)
        self.new_game_color = (60, 120, 80)
        self.new_game_hover_color = (80, 160, 110)
        self.stats_color = (60, 80, 120)
        self.stats_hover_color = (80, 110, 160)
        self.button_text_color = (255, 255, 255)
        
        # Track hover state
        self.hovering_continue = False
        self.hovering_new_game = False
        self.hovering_stats = False
        
    def handle_event(self, event: pygame.event.Event) -> None:  # type: ignore[override]
        if event.type == pygame.MOUSEMOTION:
            self.hovering_continue = self.continue_button.collidepoint(event.pos) if self.continue_button else False
            self.hovering_new_game = self.new_game_button.collidepoint(event.pos)
            self.hovering_stats = self.stats_button.collidepoint(event.pos)
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.continue_button and self.continue_button.collidepoint(event.pos):
                    # Signal transition to game screen with continue flag
                    self.finish(next_screen='continue_game')
                elif self.new_game_button.collidepoint(event.pos):
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
        
        # Draw Continue button (if save exists)
        if self.continue_button:
            continue_color = self.continue_hover_color if self.hovering_continue else self.continue_color
            pygame.draw.rect(surface, continue_color, self.continue_button, border_radius=8)
            pygame.draw.rect(surface, (200, 200, 200), self.continue_button, width=2, border_radius=8)
            
            # Draw Continue button text
            continue_text = "Continue"
            continue_text_surf = self.button_font.render(continue_text, True, self.button_text_color)
            continue_text_rect = continue_text_surf.get_rect(center=self.continue_button.center)
            surface.blit(continue_text_surf, continue_text_rect)
        
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
