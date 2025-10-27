"""Statistics screen showing lifetime player progress."""
import pygame
from .base_screen import SimpleScreen
from farkle.ui.settings import WIDTH, HEIGHT, BG_COLOR, TEXT_PRIMARY
from farkle.meta.persistence import PersistentStats


class StatisticsScreen(SimpleScreen):
    """Screen displaying lifetime statistics and personal records.
    
    Shows cumulative stats across all game sessions.
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, stats: PersistentStats):
        super().__init__()
        self.screen = screen
        self.font = font
        self.stats = stats
        
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.section_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.stats_font = pygame.font.SysFont("Arial", 20)
        
        # Back button
        button_width = 200
        button_height = 60
        button_x = WIDTH // 2 - button_width // 2
        button_y = HEIGHT - 100
        self.back_button = pygame.Rect(button_x, button_y, button_width, button_height)
        
        # Button colors
        self.button_color = (60, 80, 120)
        self.button_hover_color = (80, 110, 160)
        self.button_text_color = (255, 255, 255)
        
        # Track hover state
        self.hovering = False
    
    def handle_event(self, event: pygame.event.Event) -> None:  # type: ignore[override]
        if event.type == pygame.MOUSEMOTION:
            self.hovering = self.back_button.collidepoint(event.pos)
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.back_button.collidepoint(event.pos):
                    # Go back to menu
                    self.finish(next_screen='menu')
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC also returns to menu
                self.finish(next_screen='menu')
    
    def update(self, dt: float) -> None:  # type: ignore[override]
        pass
    
    def draw(self, surface: pygame.Surface) -> None:  # type: ignore[override]
        # Clear background
        surface.fill(BG_COLOR)
        
        # Draw title
        title_text = "LIFETIME STATISTICS"
        title_surf = self.title_font.render(title_text, True, TEXT_PRIMARY)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 50))
        surface.blit(title_surf, title_rect)
        
        # Draw Faith prominently below title (meta currency)
        if self.stats.faith > 0 or True:  # Always show faith, even if zero
            faith_text = f"Faith: {self.stats.faith}"
            faith_color = (255, 215, 100)  # Golden color for faith
            faith_surf = self.section_font.render(faith_text, True, faith_color)
            faith_rect = faith_surf.get_rect(center=(WIDTH // 2, 85))
            surface.blit(faith_surf, faith_rect)
        
        # Calculate column positions
        left_col_x = WIDTH // 4
        right_col_x = 3 * WIDTH // 4
        y_start = 120
        line_height = 30
        section_spacing = 50
        
        y = y_start
        
        # === LEFT COLUMN ===
        
        # Game Summary Section
        self._draw_section_header(surface, "GAME SUMMARY", left_col_x, y)
        y += 35
        
        y = self._draw_stat(surface, "Games Played", self.stats.total_games_played, left_col_x, y, line_height)
        y = self._draw_stat(surface, "Wins", self.stats.total_games_won, left_col_x, y, line_height)
        y = self._draw_stat(surface, "Losses", self.stats.total_games_lost, left_col_x, y, line_height)
        
        # Win rate
        if self.stats.total_games_played > 0:
            win_rate = (self.stats.total_games_won / self.stats.total_games_played) * 100
            y = self._draw_stat(surface, "Win Rate", f"{win_rate:.1f}%", left_col_x, y, line_height)
        
        y += section_spacing
        
        # Lifetime Totals Section
        self._draw_section_header(surface, "LIFETIME TOTALS", left_col_x, y)
        y += 35
        
        y = self._draw_stat(surface, "Gold Gained", self.stats.lifetime_gold_gained, left_col_x, y, line_height)
        y = self._draw_stat(surface, "Total Score", self.stats.lifetime_score, left_col_x, y, line_height)
        y = self._draw_stat(surface, "Farkles", self.stats.lifetime_farkles, left_col_x, y, line_height)
        y = self._draw_stat(surface, "Turns Played", self.stats.lifetime_turns_played, left_col_x, y, line_height)
        y = self._draw_stat(surface, "Dice Rolled", self.stats.lifetime_dice_rolled, left_col_x, y, line_height)
        
        # === RIGHT COLUMN ===
        
        y = y_start
        
        # Personal Records Section
        self._draw_section_header(surface, "PERSONAL RECORDS", right_col_x, y)
        y += 35
        
        y = self._draw_stat(surface, "Highest Single Score", self.stats.highest_single_score, right_col_x, y, line_height)
        y = self._draw_stat(surface, "Highest Game Score", self.stats.highest_game_score, right_col_x, y, line_height)
        y = self._draw_stat(surface, "Most Gold (One Game)", self.stats.most_gold_in_game, right_col_x, y, line_height)
        y = self._draw_stat(surface, "Most Turns Survived", self.stats.most_turns_survived, right_col_x, y, line_height)
        y = self._draw_stat(surface, "Furthest Day Reached", self.stats.furthest_level_reached, right_col_x, y, line_height)
        
        y += section_spacing
        
        # Progression Section
        self._draw_section_header(surface, "PROGRESSION", right_col_x, y)
        y += 35
        
        y = self._draw_stat(surface, "Relics Purchased", self.stats.lifetime_relics_purchased, right_col_x, y, line_height)
        y = self._draw_stat(surface, "Goals Completed", self.stats.lifetime_goals_completed, right_col_x, y, line_height)
        y = self._draw_stat(surface, "Levels Completed", self.stats.lifetime_levels_completed, right_col_x, y, line_height)
        
        # Achievements (if any)
        if self.stats.unlocked_achievements:
            y += section_spacing
            self._draw_section_header(surface, "ACHIEVEMENTS", right_col_x, y)
            y += 35
            for achievement in self.stats.unlocked_achievements[:5]:  # Show max 5
                achievement_surf = self.stats_font.render(f"• {achievement}", True, (220, 220, 220))
                achievement_rect = achievement_surf.get_rect(center=(right_col_x, y))
                surface.blit(achievement_surf, achievement_rect)
                y += line_height
        
        # Draw Back button
        button_color = self.button_hover_color if self.hovering else self.button_color
        pygame.draw.rect(surface, button_color, self.back_button, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), self.back_button, width=2, border_radius=8)
        
        # Draw button text
        button_text = "Back to Menu"
        button_text_surf = self.font.render(button_text, True, self.button_text_color)
        button_text_rect = button_text_surf.get_rect(center=self.back_button.center)
        surface.blit(button_text_surf, button_text_rect)
    
    def _draw_section_header(self, surface: pygame.Surface, text: str, x: int, y: int) -> None:
        """Draw a section header."""
        header_surf = self.section_font.render(text, True, (200, 220, 255))
        header_rect = header_surf.get_rect(center=(x, y))
        surface.blit(header_surf, header_rect)
    
    def _draw_stat(self, surface: pygame.Surface, label: str, value: int | str, x: int, y: int, line_height: int) -> int:
        """Draw a stat line and return next y position."""
        # Format the value
        if isinstance(value, int):
            value_str = f"{value:,}"  # Add commas for readability
        else:
            value_str = str(value)
        
        stat_text = f"{label}: {value_str}"
        stat_surf = self.stats_font.render(stat_text, True, (220, 220, 220))
        stat_rect = stat_surf.get_rect(center=(x, y))
        surface.blit(stat_surf, stat_rect)
        
        return y + line_height
