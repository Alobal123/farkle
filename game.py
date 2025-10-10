import pygame, random, sys
from game_state_manager import GameStateManager
from scoring import ScoringRules, SingleValue, ThreeOfAKind, Straight6
from die import Die
from level import Level, LevelState
from player import Player
from actions import handle_lock as action_handle_lock, handle_roll as action_handle_roll, handle_bank as action_handle_bank, handle_next_turn as action_handle_next_turn
from renderer import GameRenderer
from settings import WIDTH, HEIGHT, DICE_SIZE, MARGIN, ROLL_BTN, LOCK_BTN, BANK_BTN, NEXT_BTN

class Game:
    def __init__(self, screen, font, clock, level: Level | None = None):
        self.screen = screen
        self.font = font
        # Small font for auxiliary text
        try:
            self.small_font = pygame.font.Font(None, 22)
        except Exception:
            self.small_font = font
        self.clock = clock
        # Use provided level or default prototype (multi-goal capable)
        self.level = level or Level.single(name="Invocation Rite", target_goal=300, max_turns=2, description="Basic ritual to avert a minor omen.")
        self.level_state = LevelState(self.level)
        self.active_goal_index: int = 0
        self.rules = ScoringRules()
        self._init_rules()
        self.state_manager = GameStateManager()
        self.dice: list[Die] = []
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.level_index = 1
        # Pending scores per goal index (raw points before multiplier applied at bank time)
        self.pending_goal_scores: dict[int, int] = {}
        # Track whether at least one scoring combo has been locked since the most recent roll
        self.locked_after_last_roll = False
        # Player meta progression container
        self.player = Player()
        # Renderer handles all drawing/UI composition
        self.renderer = GameRenderer(self)
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
        # When called after win/lose we keep current level (already advanced on win)
        self.reset_dice()
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.state_manager = GameStateManager()
        self.level_state.reset()
        self.active_goal_index = 0
        self.pending_goal_scores.clear()

    def reset_turn(self):
        for d in self.dice:
            d.reset()
            d.value = random.randint(1, 6)
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.mark_scoring_dice()
        self.level_state.consume_turn()
        self.state_manager.transition_to_start()
        self.active_goal_index = 0
        self.pending_goal_scores.clear()
        self.locked_after_last_roll = False

    def roll_dice(self):
        for d in self.dice:
            if not d.held:
                d.value = random.randint(1, 6)
                d.selected = False
        # After a roll, require a new lock before rolling again
        self.locked_after_last_roll = False

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
        self.set_message("HOT DICE! You can roll all 6 dice again!")
        self.mark_scoring_dice()
        # Reset lock requirement after hot dice
        self.locked_after_last_roll = False

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

    def any_scoring_selection(self) -> bool:
        return any(d.selected and d.scoring_eligible for d in self.dice)

    def selection_is_single_combo(self) -> bool:
        """Generic: a selection is a single combo if exactly one rule fully covers it and
        its contributing indices count equals that rule's combo_size AND equals the number of selected dice.

        If multiple rules match the selection, choose the rule with the largest combo_size; if there is a tie
        (two different rule types same size) or more than one rule of that max size matches, treat as not single.
        This prevents combining smaller atomic units (e.g., two single-value dice) from counting as one combo.
        """
        selected_values = [int(d.value) for d in self.dice if d.selected]
        if not selected_values:
            return False
        matches = self.rules.evaluate_matches(selected_values)
        if not matches:
            return False
        # Filter only rules whose contributing indices span the entire selection
        full_cover = [m for m in matches if len(m[2]) == len(selected_values)]
        if not full_cover:
            return False
        # Determine max combo size among full-cover matches
        max_size = max(m[0].combo_size for m in full_cover if hasattr(m[0], 'combo_size'))
        best = [m for m in full_cover if getattr(m[0], 'combo_size', 0) == max_size]
        # Accept only if exactly one best match and its combo_size equals number of selected dice.
        if len(best) == 1 and best[0][0].combo_size == len(selected_values):
            return True
        return False

    def update_current_selection_score(self):
        if self.selection_is_single_combo():
            self.current_roll_score, _ = self.calculate_score_from_dice()
        else:
            self.current_roll_score = 0

    def _auto_lock_selection(self, verb: str = "Auto-locked") -> bool:
        """Lock selected dice if they form exactly one valid scoring combo.

        Adds raw score to pending goal, updates turn score, holds dice, updates message.
        verb: prefix for status message (e.g. 'Auto-locked', 'Locked').
        Returns True on success, False if selection invalid or score zero.
        """
        if not (self.selection_is_single_combo() and self.any_scoring_selection()):
            return False
        add_score, _ = self.calculate_score_from_dice()
        if add_score <= 0:
            return False
        self.pending_goal_scores[self.active_goal_index] = self.pending_goal_scores.get(self.active_goal_index, 0) + add_score
        self.turn_score += add_score
        self.current_roll_score = 0
        for d in self.dice:
            if d.selected:
                d.hold()
        gname = self.level.goals[self.active_goal_index][0]
        self.message = f"{verb} {add_score} to {gname}."
        self.mark_scoring_dice()
        self.locked_after_last_roll = True
        return True

    def handle_lock(self):
        action_handle_lock(self)

    def handle_roll(self):
        action_handle_roll(self)

    def handle_bank(self):
        action_handle_bank(self)

    def handle_next_turn(self):
        action_handle_next_turn(self)

    def create_next_level(self):
        self.level_index += 1
        # Delegate progression logic to Level.advance for consistency
        self.level = Level.advance(self.level, self.level_index)
        self.level_state = LevelState(self.level)
        self.active_goal_index = 0
        self.pending_goal_scores.clear()
        # Gold persists; player_gold not reset here.

    def draw(self):
        self.renderer.draw()

    # Rendering helpers moved to GameRenderer.

    def check_end_conditions(self):
        if self.level_state.completed:
            self.set_message(f"Omen averted! ({self.level.name})")
            self.draw(); pygame.time.wait(1200)
            self.create_next_level()
            self.reset_game()
        elif self.level_state.failed:
            unfinished = [self.level.goals[i][0] for i in self.level_state.mandatory_indices if not self.level_state.goals[i].is_fulfilled()]
            unf_txt = ", ".join(unfinished) if unfinished else "(none)"
            self.set_message(f"Ritual failed. Unfinished: {unf_txt}")
            self.draw(); pygame.time.wait(1200)
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
                    if hasattr(self.renderer, 'goal_boxes'):
                        for idx, rect in enumerate(self.renderer.goal_boxes):
                            if rect.collidepoint(mx, my):
                                self.active_goal_index = idx
                                break
                    if ROLL_BTN.collidepoint(mx, my):
                        current_state = self.state_manager.get_state()
                        valid_combo_selected = self.selection_is_single_combo() and self.any_scoring_selection()
                        can_roll = (current_state == self.state_manager.state.START) or (current_state == self.state_manager.state.ROLLING and (self.locked_after_last_roll or valid_combo_selected))
                        if can_roll:
                            self.handle_roll()
                        else:
                            self.set_message("Lock a scoring combo before rolling again.")
                    if LOCK_BTN.collidepoint(mx, my):
                        self.handle_lock()
                    if BANK_BTN.collidepoint(mx, my):
                        self.handle_bank()
                    if NEXT_BTN.collidepoint(mx, my):
                        self.handle_next_turn()
            self.check_end_conditions()
            self.renderer.draw()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()

    def set_message(self, text: str):
        """Set current UI status message.

        Future extension: maintain a history or timestamp for debugging/logs.
        """
        self.message = text
