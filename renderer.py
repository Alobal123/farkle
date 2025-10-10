"""GameRenderer handles all drawing and UI state computations.

Separating rendering concerns from game logic (Game class) keeps game.py smaller and
focuses Game on state transitions, scoring, and input handling.
"""
import pygame
from typing import List, Tuple
from die import Die
from settings import (
    WIDTH, HEIGHT, DICE_SIZE, MARGIN,
    BG_COLOR, BTN_ROLL_COLOR, BTN_LOCK_COLOR_DISABLED, BTN_LOCK_COLOR_ENABLED,
    BTN_BANK_COLOR, TEXT_PRIMARY, TEXT_ACCENT,
    GOAL_BG_MANDATORY, GOAL_BG_MANDATORY_DONE, GOAL_BG_OPTIONAL, GOAL_BG_OPTIONAL_DONE,
    GOAL_BORDER_ACTIVE, GOAL_TEXT, GOAL_PADDING, GOAL_WIDTH, GOAL_LINE_SPACING,
    ROLL_BTN, LOCK_BTN, BANK_BTN, NEXT_BTN
)

class GameRenderer:
    def __init__(self, game):
        self.game = game
        self.goal_boxes: List[pygame.Rect] = []

    def compute_button_states(self) -> Tuple[bool, bool, bool]:
        g = self.game
        current_state = g.state_manager.get_state()
        if current_state == g.state_manager.state.START:
            roll_enabled = True
        else:
            valid_combo = g.selection_is_single_combo() and g.any_scoring_selection()
            roll_enabled = current_state == g.state_manager.state.ROLLING and (g.locked_after_last_roll or valid_combo)
        lock_enabled = g.selection_is_single_combo() and g.any_scoring_selection() and current_state in (g.state_manager.state.START, g.state_manager.state.ROLLING)
        valid_combo = g.selection_is_single_combo() and g.any_scoring_selection()
        bank_enabled = (
            current_state == g.state_manager.state.ROLLING and (
                (g.turn_score > 0 and not any(d.selected for d in g.dice)) or valid_combo
            )
        )
        return roll_enabled, lock_enabled, bank_enabled

    def compute_preview_scores(self) -> Tuple[int, int]:
        g = self.game
        if g.selection_is_single_combo() and g.current_roll_score > 0:
            adjusted = int(g.current_roll_score * g.level.score_multiplier)
        else:
            adjusted = 0
        return g.turn_score + adjusted, adjusted

    def draw(self):
        g = self.game
        screen = g.screen
        screen.fill(BG_COLOR)
        if g.state_manager.get_state() in (g.state_manager.state.ROLLING, g.state_manager.state.FARKLE, g.state_manager.state.BANKED):
            for d in g.dice:
                d.draw(screen)
        # Buttons
        def dim(color):
            return tuple(max(0, int(c * 0.45)) for c in color)
        roll_enabled, lock_enabled, bank_enabled = self.compute_button_states()
        roll_color = BTN_ROLL_COLOR if roll_enabled else dim(BTN_ROLL_COLOR)
        lock_color = BTN_LOCK_COLOR_ENABLED if lock_enabled else dim(BTN_LOCK_COLOR_DISABLED)
        bank_color = BTN_BANK_COLOR if bank_enabled else dim(BTN_BANK_COLOR)
        pygame.draw.rect(screen, roll_color, ROLL_BTN, border_radius=10)
        pygame.draw.rect(screen, lock_color, LOCK_BTN, border_radius=10)
        pygame.draw.rect(screen, bank_color, BANK_BTN, border_radius=10)
        def label_color(enabled: bool) -> Tuple[int,int,int]:
            return (0,0,0) if enabled else (60,60,60)
        screen.blit(g.font.render("ROLL", True, label_color(roll_enabled)), (ROLL_BTN.x + 25, ROLL_BTN.y + 10))
        screen.blit(g.font.render("LOCK", True, label_color(lock_enabled)), (LOCK_BTN.x + 25, LOCK_BTN.y + 10))
        screen.blit(g.font.render("BANK", True, label_color(bank_enabled)), (BANK_BTN.x + 25, BANK_BTN.y + 10))
        if g.state_manager.get_state() in (g.state_manager.state.FARKLE, g.state_manager.state.BANKED):
            pygame.draw.rect(screen, (200, 50, 50), NEXT_BTN, border_radius=10)
            screen.blit(g.font.render("Next Turn", True, (255, 255, 255)), (NEXT_BTN.x + 10, NEXT_BTN.y + 10))
        # Status message
        screen.blit(g.font.render(g.message, True, TEXT_PRIMARY), (80, 60))
        # Score preview
        dice_bottom_y = HEIGHT // 2 - DICE_SIZE // 2 + DICE_SIZE
        score_y = dice_bottom_y + 15
        preview_score, adjusted_selection = self.compute_preview_scores()
        screen.blit(g.font.render(f"Turn Score: {preview_score}", True, TEXT_PRIMARY), (100, score_y))
        if adjusted_selection > 0:
            screen.blit(g.font.render(f"+ Selecting: {adjusted_selection}", True, TEXT_ACCENT), (100, score_y + 25))
        # Goals layout
        panel_y = 90
        self.goal_boxes = []
        spacing = 16
        total_goals = len(g.level.goals)
        left_x = 80
        right_margin = 40
        available_width = WIDTH - left_x - right_margin - (spacing * (total_goals - 1))
        per_box_width = min(GOAL_WIDTH, int(available_width / total_goals))
        per_box_width = max(140, per_box_width)
        used_width = per_box_width * total_goals + spacing * (total_goals - 1)
        start_x = left_x + (available_width - used_width) // 2 if used_width < available_width else left_x
        max_box_height = 0
        prepared = []
        for i, goal in enumerate(g.level_state.goals):
            base_remaining = goal.get_remaining()
            pending_raw = g.pending_goal_scores.get(i, 0)
            pending_adjusted = int(pending_raw * g.level.score_multiplier) if pending_raw else 0
            if goal.is_fulfilled():
                remaining_text = "Done"
            else:
                if pending_adjusted > 0:
                    show_remaining = max(0, base_remaining - pending_adjusted)
                    remaining_text = f"Rem: {base_remaining} (-{pending_raw} * {g.level.score_multiplier:.2f} = {pending_adjusted}) -> {show_remaining}"
                else:
                    remaining_text = f"Rem: {base_remaining}"
            reward_text = f"Reward: {goal.reward_gold}g" if goal.reward_gold > 0 else ""
            base_desc = g.level.description if i == 0 else ""
            desc = (base_desc + ("\n" + reward_text if base_desc and reward_text else reward_text)).strip()
            lines_out = goal.build_lines(g.small_font, per_box_width, remaining_text, desc, GOAL_PADDING, GOAL_LINE_SPACING)
            box_height = goal.compute_box_height(g.small_font, lines_out, GOAL_PADDING, GOAL_LINE_SPACING)
            prepared.append((goal, lines_out, box_height))
            if box_height > max_box_height:
                max_box_height = box_height
        x = start_x
        for i, (goal, lines_out, box_height) in enumerate(prepared):
            box_rect = pygame.Rect(x, panel_y, per_box_width, max_box_height)
            self.goal_boxes.append(box_rect)
            if goal.mandatory:
                bg = GOAL_BG_MANDATORY_DONE if goal.is_fulfilled() else GOAL_BG_MANDATORY
            else:
                bg = GOAL_BG_OPTIONAL_DONE if goal.is_fulfilled() else GOAL_BG_OPTIONAL
            pygame.draw.rect(screen, bg, box_rect, border_radius=10)
            if i == g.active_goal_index:
                pygame.draw.rect(screen, GOAL_BORDER_ACTIVE, box_rect, width=3, border_radius=10)
            goal.draw_into(screen, box_rect, g.small_font, lines_out, GOAL_PADDING, GOAL_LINE_SPACING, GOAL_TEXT)
            x += per_box_width + spacing
        screen.blit(g.font.render(f"Level {g.level_index}", True, (180, 220, 255)), (80, 30))
        turns_text = g.small_font.render(f"Turns Left: {g.level_state.turns_left}", True, (240,240,240))
        screen.blit(turns_text, (WIDTH - turns_text.get_width() - 20, 28))
        gold_text = g.small_font.render(f"Gold: {g.player.gold}", True, (255, 215, 0))
        screen.blit(gold_text, (WIDTH - gold_text.get_width() - 20, 50))
        pygame.display.flip()

# Note: Avoid importing Game for type checking to prevent circular dependency.
