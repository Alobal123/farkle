"""Game over screen showing results and returning to main menu."""
import pygame
from typing import Any
from .base_screen import SimpleScreen
from farkle.ui.settings import WIDTH, HEIGHT, BG_COLOR, TEXT_PRIMARY


class GameOverScreen(SimpleScreen):
    """Game over screen displaying failure/victory message with return to menu option.
    
    Shows:
    - Result (failure/victory)
    - Day number
    - Game statistics (gold, farkles, score)
    - Return to Menu button
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, 
                 success: bool, level_name: str, level_index: int, 
                 unfinished_goals: list[str] | None = None,
                 statistics: dict[str, Any] | None = None):
        super().__init__()
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.SysFont("Arial", 60, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 32)
        self.button_font = pygame.font.SysFont("Arial", 36)
        self.stats_font = pygame.font.SysFont("Arial", 20)  # Smaller font for stats
        
        self.success = success
        self.level_name = level_name
        self.level_index = level_index
        self.statistics = statistics or {}
        
        # Return to Menu button
        button_width = 300
        button_height = 80
        button_x = WIDTH // 2 - button_width // 2
        button_y = HEIGHT - 150
        self.menu_button = pygame.Rect(button_x, button_y, button_width, button_height)
        
        # Button colors
        self.button_color = (80, 120, 160)
        self.button_hover_color = (100, 150, 200)
        self.button_text_color = (255, 255, 255)
        
        # Track hover state
        self.hovering = False
        
        # Auto-return timer (optional - can be removed if you want manual only)
        self.auto_return_delay = 10.0  # seconds
        self.elapsed_time = 0.0
        
    def handle_event(self, event: pygame.event.Event) -> None:  # type: ignore[override]
        if event.type == pygame.MOUSEMOTION:
            self.hovering = self.menu_button.collidepoint(event.pos)
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.menu_button.collidepoint(event.pos):
                    # Signal transition to menu screen
                    self.finish(next_screen='menu')
        
        elif event.type == pygame.KEYDOWN:
            # Allow ESC or SPACE to return to menu
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                self.finish(next_screen='menu')
    
    def update(self, dt: float) -> None:  # type: ignore[override]
        # Track time for auto-return (optional)
        self.elapsed_time += dt
        # Uncomment to enable auto-return to menu:
        # if self.elapsed_time >= self.auto_return_delay:
        #     self.finish(next_screen='menu')
    
    def draw(self, surface: pygame.Surface) -> None:  # type: ignore[override]
        # Clear background
        surface.fill(BG_COLOR)
        
        # Title: Success or Failure
        if self.success:
            title_text = "VICTORY!"
            title_color = (100, 220, 100)
        else:
            title_text = "DEFEAT"
            title_color = (220, 100, 100)
            
        title_surf = self.title_font.render(title_text, True, title_color)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 4 - 40))
        surface.blit(title_surf, title_rect)
        
        # Day info - display as "Day X: disaster name"
        level_text = f"Day {self.level_index}: {self.level_name}"
        level_surf = self.subtitle_font.render(level_text, True, TEXT_PRIMARY)
        level_rect = level_surf.get_rect(center=(WIDTH // 2, HEIGHT // 4 + 20))
        surface.blit(level_surf, level_rect)
        
        # Statistics section
        y_offset = HEIGHT // 4 + 80
        
        # Display gold stats
        gold_data = self.statistics.get('gold', {})
        gold_text = f"Total Gold Gained: {gold_data.get('total', 0)}"
        gold_surf = self.stats_font.render(gold_text, True, (255, 215, 0))
        gold_rect = gold_surf.get_rect(center=(WIDTH // 2, y_offset))
        surface.blit(gold_surf, gold_rect)
        y_offset += 35
        
        # Display farkle stats
        farkle_data = self.statistics.get('farkles', {})
        farkle_text = f"Total Farkles: {farkle_data.get('total', 0)}"
        farkle_surf = self.stats_font.render(farkle_text, True, (220, 100, 100))
        farkle_rect = farkle_surf.get_rect(center=(WIDTH // 2, y_offset))
        surface.blit(farkle_surf, farkle_rect)
        y_offset += 35
        
        # Display scoring stats
        scoring_data = self.statistics.get('scoring', {})
        score_text = f"Total Score: {scoring_data.get('total_score', 0)}"
        score_surf = self.stats_font.render(score_text, True, (150, 200, 255))
        score_rect = score_surf.get_rect(center=(WIDTH // 2, y_offset))
        surface.blit(score_surf, score_rect)
        y_offset += 35
        
        # Display highest single score
        highest_text = f"Highest Single Score: {scoring_data.get('highest_single', 0)}"
        highest_surf = self.stats_font.render(highest_text, True, (200, 150, 255))
        highest_rect = highest_surf.get_rect(center=(WIDTH // 2, y_offset))
        surface.blit(highest_surf, highest_rect)
        y_offset += 35
        
        # Display gameplay stats
        gameplay_data = self.statistics.get('gameplay', {})
        turns_text = f"Turns Played: {gameplay_data.get('turns_played', 0)}"
        turns_surf = self.stats_font.render(turns_text, True, (180, 180, 180))
        turns_rect = turns_surf.get_rect(center=(WIDTH // 2, y_offset))
        surface.blit(turns_surf, turns_rect)
        y_offset += 30
        
        relics_text = f"Relics Purchased: {gameplay_data.get('relics_purchased', 0)}"
        relics_surf = self.stats_font.render(relics_text, True, (180, 180, 180))
        relics_rect = relics_surf.get_rect(center=(WIDTH // 2, y_offset))
        surface.blit(relics_surf, relics_rect)
        y_offset += 30
        
        goals_text = f"Goals Completed: {gameplay_data.get('goals_completed', 0)}"
        goals_surf = self.stats_font.render(goals_text, True, (180, 180, 180))
        goals_rect = goals_surf.get_rect(center=(WIDTH // 2, y_offset))
        surface.blit(goals_surf, goals_rect)
        
        # Return to Menu button
        button_color = self.button_hover_color if self.hovering else self.button_color
        pygame.draw.rect(surface, button_color, self.menu_button, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), self.menu_button, width=2, border_radius=8)
        
        # Draw button text
        button_text = "Return to Menu"
        button_text_surf = self.button_font.render(button_text, True, self.button_text_color)
        button_text_rect = button_text_surf.get_rect(center=self.menu_button.center)
        surface.blit(button_text_surf, button_text_rect)
        
        # Hint text
        hint_text = "Press SPACE or ESC to continue"
        hint_surf = pygame.font.SysFont("Arial", 20).render(hint_text, True, (150, 150, 150))
        hint_rect = hint_surf.get_rect(center=(WIDTH // 2, HEIGHT - 50))
        surface.blit(hint_surf, hint_rect)
