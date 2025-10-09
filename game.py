import pygame, random, sys
from game_state_manager import GameStateManager
from goal import Goal
from scoring import ScoringRules, SingleValue, ThreeOfAKind, Straight6
from die import Die

# Shared UI constants (expect pygame.init done by caller)
WIDTH, HEIGHT = 800, 600
DICE_SIZE = 80
MARGIN = 20
ROLL_BTN = pygame.Rect(WIDTH//2 - 200, HEIGHT - 100, 120, 50)
LOCK_BTN = pygame.Rect(WIDTH//2 - 60, HEIGHT - 100, 120, 50)
BANK_BTN = pygame.Rect(WIDTH//2 + 80, HEIGHT - 100, 120, 50)
NEXT_BTN = pygame.Rect(WIDTH//2 - 60, HEIGHT - 160, 120, 50)

class Game:
    def __init__(self, screen, font, clock, target_goal: int = 2000, max_turns: int = 2):
        self.screen = screen
        self.font = font
        self.clock = clock
        self.target_goal = target_goal
        self.max_turns = max_turns
        self.rules = ScoringRules()
        self._init_rules()
        self.state_manager = GameStateManager()
        self.dice: list[Die] = []
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.goal = Goal(self.target_goal)
        self.turns_left = self.max_turns
        self.reset_dice()

    def _init_rules(self):
        self.rules.add_rule(ThreeOfAKind(1, 1000))
        self.rules.add_rule(ThreeOfAKind(2, 200))
        self.rules.add_rule(ThreeOfAKind(3, 300))
        self.rules.add_rule(ThreeOfAKind(4, 400))
        self.rules.add_rule(ThreeOfAKind(5, 500))
        self.rules.add_rule(ThreeOfAKind(6, 600))
        self.rules.add_rule(SingleValue(1, 100))
        self.rules.add_rule(SingleValue(5, 50))
        self.rules.add_rule(Straight6(1500))

    def reset_dice(self):
        self.dice = [Die(random.randint(1, 6), 100 + i * (DICE_SIZE + MARGIN), HEIGHT // 2 - DICE_SIZE // 2) for i in range(6)]

    def reset_game(self):
        self.reset_dice()
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.state_manager = GameStateManager()
        self.goal = Goal(self.target_goal)
        self.turns_left = self.max_turns

    def reset_turn(self):
        for d in self.dice:
            d.reset()
            d.value = random.randint(1, 6)
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.mark_scoring_dice()
        self.turns_left = max(0, self.turns_left - 1)
        self.state_manager.transition_to_start()

    def roll_dice(self):
        for d in self.dice:
            if not d.held:
                d.value = random.randint(1, 6)
                d.selected = False

    def calculate_score_from_dice(self):
        selected: list[int] = [int(d.value) for d in self.dice if d.selected]
        if not selected:
            return 0, []
        return self.rules.evaluate(selected)

    def check_farkle(self):
        unheld = [d for d in self.dice if not d.held]
        if not unheld:
            return False
        values: list[int] = [int(d.value) for d in unheld]
        score, _ = self.rules.evaluate(values)
        return score == 0

    def all_dice_held(self):
        return all(d.held for d in self.dice)

    def hot_dice_reset(self):
        for d in self.dice:
            d.reset()
            d.value = random.randint(1, 6)
        self.message = "HOT DICE! You can roll all 6 dice again!"
        self.mark_scoring_dice()

    def can_roll_again(self):
        return self.state_manager.get_state() == self.state_manager.state.START or any(d.held for d in self.dice)

    def mark_scoring_dice(self):
        for d in self.dice:
            d.scoring_eligible = False
        unheld = [d for d in self.dice if not d.held]
        if not unheld:
            return
        values: list[int] = [int(d.value) for d in unheld]
        score, contributing = self.rules.evaluate(values)
        for i in contributing:
            unheld[i].scoring_eligible = True

    def has_partial_set_selected(self) -> bool:
        if self.state_manager.get_state() != self.state_manager.state.ROLLING:
            return False
        unheld = [d for d in self.dice if not d.held]
        counts = {}
        for d in unheld:
            counts[d.value] = counts.get(d.value, 0) + 1
        for value, cnt in counts.items():
            if cnt >= 3:
                selected_cnt = sum(1 for d in unheld if d.value == value and d.selected)
                if 0 < selected_cnt < 3:
                    return True
        return False

    def any_scoring_selection(self) -> bool:
        return any(d.selected and d.scoring_eligible for d in self.dice)

    def selection_is_single_combo(self) -> bool:
        """Return True if current selection corresponds to exactly one scoring rule.
        We treat a valid combo as either:
          - Exactly the contributing dice for one rule evaluation (e.g., triple, straight, singles of same face)
        Mixed singles (e.g., a 1 and a 5 together) count as multiple combos and are disallowed.
        """
        selected_values = [d.value for d in self.dice if d.selected]
        if not selected_values:
            return False
        # Evaluate full selection using rules; we need to detect if multiple distinct scoring groups are present.
        # Approach: count occurrences; if length > 1 and not all same and not straight and not triple-of-kind alone, reject.
        from collections import Counter
        c = Counter(selected_values)
        # Straight case (must be exactly 6 unique forming 1..6)
        if sorted(selected_values) == [1,2,3,4,5,6]:
            return True
        if len(c) == 1:
            # All same value. Accept only if size is 1 (single allowed only if value is 1 or 5) or exactly 3 for triple handled by rules.
            v = next(iter(c))
            count = c[v]
            if count == 1 and v in (1,5):
                return True
            if count == 3:
                return True
            # Could extend for 4/5/6 of a kind later; for now restrict.
            return False
        # Multiple distinct values.
        # If all are singles AND exactly one scoring single (should be length 1, already handled) -> unreachable here.
        # Mixed 1s and 5s is multiple combos => False
        return False

    def update_current_selection_score(self):
        if self.selection_is_single_combo():
            self.current_roll_score, _ = self.calculate_score_from_dice()
        else:
            self.current_roll_score = 0

    def handle_lock(self):
        if self.state_manager.get_state() not in (self.state_manager.state.START, self.state_manager.state.ROLLING):
            return
        if not self.any_scoring_selection():
            self.message = "Select scoring dice first."
            return
        if not self.selection_is_single_combo():
            self.message = "Lock only one combo at a time."
            return
        if self.has_partial_set_selected():
            self.message = "Select ALL dice of the three-of-a-kind or deselect them."
            return
        if self.state_manager.get_state() == self.state_manager.state.START:
            self.state_manager.transition_to_rolling()
        add_score, _ = self.calculate_score_from_dice()
        if add_score <= 0:
            self.message = "No score in selection."
            return
        self.turn_score += add_score
        self.current_roll_score = 0
        for d in self.dice:
            if d.selected:
                d.hold()
        self.message = f"Locked {add_score} points. Roll or lock more." if self.turn_score > 0 else "Select dice to lock."
        self.mark_scoring_dice()

    def handle_roll(self):
        if any(d.selected for d in self.dice):
            self.message = "Lock selected dice before rolling."
            return
        if not self.can_roll_again():
            self.message = "You must lock at least one scoring die first!"
            return
        if self.state_manager.get_state() == self.state_manager.state.START:
            self.state_manager.transition_to_rolling()
        if self.all_dice_held():
            self.hot_dice_reset()
            self.message = "HOT DICE! Roll all 6 again!"
        else:
            self.roll_dice()
        self.mark_scoring_dice()
        if self.check_farkle():
            self.state_manager.transition_to_farkle()
            self.message = "Farkle! You lose this turn's points."
            self.turn_score = 0
            self.current_roll_score = 0

    def handle_bank(self):
        if self.state_manager.get_state() != self.state_manager.state.ROLLING:
            return
        if any(d.selected for d in self.dice):
            self.message = "Lock or deselect dice before banking."
            return
        if (self.turn_score) <= 0:
            return
        banked_points = self.turn_score
        self.goal.subtract(banked_points)
        self.turn_score = 0
        self.current_roll_score = 0
        self.state_manager.transition_to_banked()
        if self.goal.is_fulfilled():
            self.message = f"Goal fulfilled! You reached {self.goal.target_score} points!"
        else:
            self.message = f"Banked {banked_points} points! Points to goal: {self.goal.get_remaining()}"

    def handle_next_turn(self):
        if self.state_manager.get_state() in (self.state_manager.state.FARKLE, self.state_manager.state.BANKED):
            self.reset_turn()

    def draw(self):
        self.screen.fill((40, 120, 40))
        if self.state_manager.get_state() in (self.state_manager.state.ROLLING, self.state_manager.state.FARKLE, self.state_manager.state.BANKED):
            for d in self.dice:
                d.draw(self.screen)
        # Buttons
        pygame.draw.rect(self.screen, (250, 200, 50), ROLL_BTN, border_radius=10)
        lock_enabled = self.selection_is_single_combo() and self.any_scoring_selection() and not self.has_partial_set_selected()
        lock_color = (180, 180, 250) if lock_enabled else (120, 120, 150)
        pygame.draw.rect(self.screen, lock_color, LOCK_BTN, border_radius=10)
        pygame.draw.rect(self.screen, (100, 200, 100), BANK_BTN, border_radius=10)
        self.screen.blit(self.font.render("ROLL", True, (0, 0, 0)), (ROLL_BTN.x + 25, ROLL_BTN.y + 10))
        self.screen.blit(self.font.render("LOCK", True, (0, 0, 0)), (LOCK_BTN.x + 25, LOCK_BTN.y + 10))
        self.screen.blit(self.font.render("BANK", True, (0, 0, 0)), (BANK_BTN.x + 25, BANK_BTN.y + 10))
        if self.state_manager.get_state() in (self.state_manager.state.FARKLE, self.state_manager.state.BANKED):
            pygame.draw.rect(self.screen, (200, 50, 50), NEXT_BTN, border_radius=10)
            self.screen.blit(self.font.render("Next Turn", True, (255, 255, 255)), (NEXT_BTN.x + 10, NEXT_BTN.y + 10))
        # Info lines
        self.screen.blit(self.font.render(self.message, True, (255, 255, 255)), (80, 60))
        # Live turn score preview includes locked plus current selection (if valid)
        preview_score = self.turn_score + (self.current_roll_score if self.selection_is_single_combo() else 0)
        self.screen.blit(self.font.render(f"Turn Score: {preview_score}", True, (255, 255, 255)), (80, 100))
        if self.selection_is_single_combo() and self.current_roll_score > 0:
            self.screen.blit(self.font.render(f"+ Selecting: {self.current_roll_score}", True, (200, 200, 50)), (80, 130))
            y_goal = 160
        else:
            y_goal = 130
        self.screen.blit(self.font.render(f"Points to Goal: {self.goal.get_remaining()}", True, (255, 255, 0)), (80, y_goal))
        circle_radius = 12
        circle_margin = 8
        for i in range(self.turns_left):
            x = WIDTH - 30 - i * (circle_radius * 2 + circle_margin)
            y = 30
            pygame.draw.circle(self.screen, (0, 0, 0), (x, y), circle_radius)
        pygame.display.flip()

    def check_end_conditions(self):
        if self.goal.is_fulfilled():
            self.message = f"Congratulations! You win! Goal of {self.goal.target_score} reached!"
            self.draw()
            pygame.time.wait(2000)
            self.reset_game()
        elif self.turns_left <= 0 and not self.goal.is_fulfilled():
            self.message = "Sorry, you lose! Goal not reached in time."
            self.draw()
            pygame.time.wait(2000)
            self.reset_game()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    for d in self.dice:
                        if self.state_manager.get_state() == self.state_manager.state.ROLLING and d.rect().collidepoint(mx, my):
                            if not d.held and d.scoring_eligible:
                                d.toggle_select()
                                self.update_current_selection_score()
                    if ROLL_BTN.collidepoint(mx, my) and self.state_manager.get_state() in (self.state_manager.state.START, self.state_manager.state.ROLLING):
                        self.handle_roll()
                    if LOCK_BTN.collidepoint(mx, my):
                        self.handle_lock()
                    if BANK_BTN.collidepoint(mx, my):
                        self.handle_bank()
                    if NEXT_BTN.collidepoint(mx, my):
                        self.handle_next_turn()
            self.check_end_conditions()
            self.draw()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()
