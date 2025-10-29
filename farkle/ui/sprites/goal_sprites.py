import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer
from farkle.ui.settings import DICE_TARGET_SELECTION

class GoalSprite(BaseSprite):
    """Sprite rendering for a Goal replicating Goal.draw logic.

    Each sync recomputes layout based on index and score progress.
    """
    def __init__(self, goal, game, *groups):
        super().__init__(Layer.UI, goal, *groups)
        self.goal = goal
        self.game = game
        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sync_from_logical()

    def sync_from_logical(self):
        g = self.game
        goal = self.goal
        if not g:
            return
        # Hide goals during SHOP so shop is visually dominant
        try:
            if g.state_manager.get_state().name == 'SHOP':
                self.image.fill((0,0,0,0))
                self.rect.topleft = (-1000,-1000)
                self.dirty = 1
                return
        except Exception:
            pass
        from farkle.ui.settings import WIDTH, GOAL_PADDING, GOAL_LINE_SPACING, GOAL_WIDTH
        # Determine index & layout
        goals = g.level_state.goals
        try:
            idx = goals.index(goal)
        except ValueError:
            return
        
        # New layout: disasters in center, petitions stacked on sides
        is_disaster = goal.is_disaster
        
        disaster_goals = [g for g in goals if g.is_disaster]
        petition_goals = [g for g in goals if not g.is_disaster]
        
        # --- Sizing ---
        spacing = 16
        disaster_width = int(GOAL_WIDTH * 1.8)
        petition_width = GOAL_WIDTH

        disaster_height = 140
        petition_height = 100
        
        # --- Positioning ---
        top_offset = 140 # Move goals down to make space for relic panel
        if is_disaster:
            per_box_width = disaster_width
            x = (WIDTH - per_box_width) // 2
            panel_y = top_offset 
        else:
            per_box_width = petition_width
            left_goals = petition_goals[::2]
            right_goals = petition_goals[1::2]
            
            disaster_y_start = top_offset
            disaster_center_y = disaster_y_start + (disaster_height / 2)
            
            top_petition_y = disaster_center_y - petition_height
            
            little_gap = 10
            bottom_petition_y = disaster_center_y + little_gap

            try:
                if goal in left_goals:
                    idx_in_col = left_goals.index(goal)
                    x = (WIDTH // 2) - disaster_width // 2 - spacing - per_box_width
                    panel_y = top_petition_y if idx_in_col == 0 else bottom_petition_y
                elif goal in right_goals:
                    idx_in_col = right_goals.index(goal)
                    x = (WIDTH // 2) + disaster_width // 2 + spacing
                    panel_y = top_petition_y if idx_in_col == 0 else bottom_petition_y
                else:
                    x, panel_y = -1000, -1000 # Should not happen
            except ValueError:
                x, panel_y = -1000, -1000
        
        base_remaining = goal.get_remaining()
        pending_raw = getattr(goal, 'pending_raw', 0)
        applied = goal.target_score - base_remaining
        projected_pending = 0
        if not goal.is_fulfilled() and pending_raw > 0:
            try:
                projected_pending = max(0, goal.projected_pending())
            except Exception:
                projected_pending = pending_raw
        preview_add = 0
        try:
            if g.selection_is_single_combo() and g.any_scoring_selection():
                preview_tuple = g.selection_preview()
                if isinstance(preview_tuple, tuple) and len(preview_tuple) >= 3 and g.active_goal_index == goals.index(goal):
                    preview_add = int(preview_tuple[2])
        except Exception:
            preview_add = 0
        
        # Remove [M]/[O] tags - just use the goal name
        header = goal.name
        lines_out: list[str] = []
        for raw_line in header.split("\n"):
            wrapped = goal.wrap_text(g.small_font, raw_line, per_box_width - 2 * GOAL_PADDING)
            lines_out.extend(wrapped)
        reward_reserved_height = 20
        bar_reserved_height = 18
        
        # Use same font size for all goals in single-line layout
        font_for_height = g.small_font
        line_height = font_for_height.get_height() + GOAL_LINE_SPACING
        
        # Adjust box height for disaster goal
        if is_disaster:
            box_height = disaster_height
        else:
            box_height = petition_height
        
        # Rebuild surface
        self.image = pygame.Surface((per_box_width, box_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, panel_y))
        goal._last_rect = self.rect
        goal._last_lines = lines_out
        from farkle.ui.settings import GOAL_BORDER_ACTIVE, GOAL_TEXT
        
        # Use category-based colors
        bg, border = goal.get_category_colors(goal.category, goal.is_fulfilled())
        
        pygame.draw.rect(self.image, bg, self.image.get_rect(), border_radius=10)
        
        # Check if this goal is selected as an ability target
        is_target_selected = False
        try:
            abm = getattr(g, 'ability_manager', None)
            if abm and g.state_manager.get_state() == g.state_manager.state.SELECTING_TARGETS:
                selecting_ability = abm.selecting_ability()
                if selecting_ability and selecting_ability.target_type == 'goal':
                    collected = getattr(selecting_ability, 'collected_targets', [])
                    if idx in collected:
                        is_target_selected = True
        except Exception:
            pass
        
        # Draw borders: ability target selection takes precedence
        if is_target_selected:
            # Same blue border as dice banking selection for consistency
            pygame.draw.rect(self.image, DICE_TARGET_SELECTION, self.image.get_rect(), width=4, border_radius=10)
        elif g.active_goal_index == idx:
            pygame.draw.rect(self.image, GOAL_BORDER_ACTIVE, self.image.get_rect(), width=3, border_radius=10)
        
        # --- Content Rendering ---
        text_font = g.font if is_disaster else g.small_font
        
        # Calculate total height of all content for vertical centering
        total_text_height = sum(text_font.get_height() for ln in lines_out) + (len(lines_out) - 1) * GOAL_LINE_SPACING
        content_spacing = 8 # Space between text, bar, and reward
        total_content_height = total_text_height + content_spacing + bar_reserved_height + content_spacing + reward_reserved_height
        
        # Start rendering from a vertically centered position
        y_pos = (box_height - total_content_height) // 2

        # 1. Render Title Text
        for ln in lines_out:
            surf = text_font.render(ln, True, GOAL_TEXT)
            x_pos = (self.image.get_width() - surf.get_width()) // 2
            self.image.blit(surf, (x_pos, y_pos))
            y_pos += text_font.get_height() + GOAL_LINE_SPACING
        
        y_pos += content_spacing

        # 2. Render Progress Bar
        bar_margin = 6
        bar_height = 14
        bar_x = bar_margin
        bar_y = y_pos
        bar_width = self.image.get_width() - bar_margin * 2
        track_color = (50, 55, 60)
        pygame.draw.rect(self.image, track_color, pygame.Rect(bar_x, bar_y, bar_width, bar_height), border_radius=4)
        total = max(1, goal.target_score)
        applied_w = int(bar_width * applied / total)
        pending_w = int(bar_width * projected_pending / total)
        preview_w = int(bar_width * preview_add / total)
        if applied_w > bar_width:
            applied_w = bar_width; pending_w = 0; preview_w = 0
        else:
            if applied_w + pending_w > bar_width:
                pending_w = max(0, bar_width - applied_w); preview_w = 0
            if applied_w + pending_w + preview_w > bar_width:
                preview_w = max(0, bar_width - applied_w - pending_w)
        goal._last_bar_widths = {
            'applied': applied_w,
            'pending': pending_w,
            'preview': preview_w,
            'total': bar_width
        }
        applied_color = (70, 180, 110)
        pending_color = (200, 150, 60)
        preview_color = (110, 140, 220)
        if applied_w > 0:
            pygame.draw.rect(self.image, applied_color, pygame.Rect(bar_x, bar_y, applied_w, bar_height), border_radius=4)
        if pending_w > 0:
            pygame.draw.rect(self.image, pending_color, pygame.Rect(bar_x + applied_w, bar_y, pending_w, bar_height))
        if preview_w > 0:
            pygame.draw.rect(self.image, preview_color, pygame.Rect(bar_x + applied_w + pending_w, bar_y, preview_w, bar_height))
        summary = f"{applied}/{goal.target_score}"
        if projected_pending:
            summary += f"+{projected_pending}"
        if preview_add:
            summary += f"+{preview_add}"
        summary_surf = g.small_font.render(summary, True, (230,230,228))
        summary_x = (self.image.get_width() - summary_surf.get_width()) // 2
        self.image.blit(summary_surf, (summary_x, bar_y - 1))

        y_pos += bar_height + content_spacing

        # 3. Render Reward Text
        if goal.reward_gold > 0:
            reward_text = f"Gold {goal.reward_gold}"
            reward_surf = g.small_font.render(reward_text, True, GOAL_TEXT)
            reward_x = (self.image.get_width() - reward_surf.get_width()) // 2
            reward_y = y_pos
            self.image.blit(reward_surf, (reward_x, reward_y))
        elif goal.reward_income > 0:
            reward_text = f"+{goal.reward_income} Income"
            reward_surf = g.small_font.render(reward_text, True, GOAL_TEXT)
            reward_x = (self.image.get_width() - reward_surf.get_width()) // 2
            reward_y = y_pos
            self.image.blit(reward_surf, (reward_x, reward_y))
        elif goal.reward_blessing:
            # Map blessing types to short display names
            blessing_display = {
                "double_score": "Divine Fortune"
            }.get(goal.reward_blessing, goal.reward_blessing)
            reward_text = blessing_display
            reward_surf = g.small_font.render(reward_text, True, GOAL_TEXT)
            reward_x = (self.image.get_width() - reward_surf.get_width()) // 2
            reward_y = y_pos
            self.image.blit(reward_surf, (reward_x, reward_y))
        elif goal.reward_faith > 0:
            reward_text = f"+{goal.reward_faith} Faith"
            reward_surf = g.small_font.render(reward_text, True, (240, 230, 140))  # Golden color for faith
            reward_x = (self.image.get_width() - reward_surf.get_width()) // 2
            reward_y = y_pos
            self.image.blit(reward_surf, (reward_x, reward_y))

        self.dirty = 1

    def handle_click(self, game, pos):
        """Handle clicks on goals for target selection (e.g., sanctify ability)."""
        mx, my = pos
        if not self.rect.collidepoint(mx, my):
            return False
        
        # Check if we're in target selection mode for a goal-targeting ability
        try:
            ability_mgr = getattr(game, 'ability_manager', None)
            if not ability_mgr:
                return False
            
            selecting_ability = ability_mgr.selecting_ability()
            if not selecting_ability:
                return False
            
            # Check if this ability targets goals
            if getattr(selecting_ability, 'target_type', None) != 'goal':
                return False
            
            # Get goal index
            goals = game.level_state.goals
            try:
                goal_index = goals.index(self.goal)
            except (ValueError, AttributeError):
                return False
            
            # Attempt to use ability on this goal
            if ability_mgr.attempt_target('goal', goal_index):
                return True
                
        except Exception:
            pass
        
        return False


__all__ = ["GoalSprite"]
