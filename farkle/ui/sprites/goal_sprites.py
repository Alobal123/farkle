import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer

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
        total_goals = len(goals)
        spacing = 16
        left_x = 80
        right_margin = 40
        available_width = WIDTH - left_x - right_margin - (spacing * (total_goals - 1))
        per_box_width = min(GOAL_WIDTH, int(available_width / total_goals))
        per_box_width = max(140, per_box_width)
        used_width = per_box_width * total_goals + spacing * (total_goals - 1)
        start_x = left_x + (available_width - used_width) // 2 if used_width < available_width else left_x
        x = start_x + idx * (per_box_width + spacing)
        base_remaining = goal.get_remaining()
        pending_raw = getattr(goal, 'pending_raw', 0)
        applied = goal.target_score - base_remaining
        projected_pending = 0
        if not goal.is_fulfilled() and pending_raw > 0:
            try:
                projected_pending = max(0, g.compute_goal_pending_final(goal))
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
        tag = "M" if goal.mandatory else "O"
        header = f"{goal.name} [{tag}]"
        lines_out: list[str] = []
        for raw_line in header.split("\n"):
            wrapped = goal.wrap_text(g.small_font, raw_line, per_box_width - 2 * GOAL_PADDING)
            lines_out.extend(wrapped)
        bar_reserved_height = 20
        box_height = GOAL_PADDING * 2 + len(lines_out) * (g.small_font.get_height() + GOAL_LINE_SPACING) - GOAL_LINE_SPACING + bar_reserved_height
        panel_y = 90
        # Rebuild surface
        self.image = pygame.Surface((per_box_width, box_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, panel_y))
        goal._last_rect = self.rect
        goal._last_lines = lines_out
        from farkle.ui.settings import (
            GOAL_BG_MANDATORY, GOAL_BG_MANDATORY_DONE, GOAL_BG_OPTIONAL, GOAL_BG_OPTIONAL_DONE,
            GOAL_BORDER_ACTIVE, GOAL_TEXT
        )
        if goal.mandatory:
            bg = GOAL_BG_MANDATORY_DONE if goal.is_fulfilled() else GOAL_BG_MANDATORY
        else:
            bg = GOAL_BG_OPTIONAL_DONE if goal.is_fulfilled() else GOAL_BG_OPTIONAL
        pygame.draw.rect(self.image, bg, self.image.get_rect(), border_radius=10)
        if g.active_goal_index == idx:
            pygame.draw.rect(self.image, GOAL_BORDER_ACTIVE, self.image.get_rect(), width=3, border_radius=10)
        y_line = GOAL_PADDING
        for ln in lines_out:
            self.image.blit(g.small_font.render(ln, True, GOAL_TEXT), (GOAL_PADDING, y_line))
            y_line += g.small_font.get_height() + GOAL_LINE_SPACING
        # Progress bar
        bar_margin = 6
        bar_height = 14
        bar_x = bar_margin
        bar_y = self.image.get_height() - bar_margin - bar_height
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
        self.image.blit(g.small_font.render(summary, True, (230,230,228)), (bar_x + 4, bar_y - 1))
        self.dirty = 1

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
        # Human-readable concise lines: just relic names (omit effect details)
        lines = [r.name for r in relics]
        small_font = g.small_font
        rpad = 6
        r_line_surfs = [small_font.render(ln, True, (225,230,235)) for ln in lines]
        from farkle.ui.settings import WIDTH, HEIGHT
        width = max(s.get_width() for s in r_line_surfs) + rpad*2
        height = sum(s.get_height() for s in r_line_surfs) + rpad*2 + 4
        # Position: flush right, vertically centered-ish below level header
        x = WIDTH - width - 12
        top_margin = 80  # below goals/hud
        y = top_margin
        # Constrain if too tall
        if y + height > HEIGHT - 20:
            height = HEIGHT - 20 - y
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x,y))
        pygame.draw.rect(self.image, (30,45,58), self.image.get_rect(), border_radius=6)
        pygame.draw.rect(self.image, (95,140,175), self.image.get_rect(), width=1, border_radius=6)
        cur_y = rpad
        for rs in r_line_surfs:
            if cur_y + rs.get_height() + rpad > self.image.get_height():
                break
            self.image.blit(rs, (rpad, cur_y))
            cur_y += rs.get_height() + 2
        panel._last_rect = self.rect
        self.dirty = 1

__all__ = ["GoalSprite", "RelicPanelSprite"]
