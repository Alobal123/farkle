import pygame, random, sys
from game_state_enum import GameState
from scoring import ScoringRules, SingleValue, ThreeOfAKind, Straight6
from die import Die

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Farkle - Push Your Luck")
font = pygame.font.SysFont("Arial", 26)
clock = pygame.time.Clock()

DICE_SIZE = 80
MARGIN = 20
ROLL_BTN = pygame.Rect(WIDTH//2 - 140, HEIGHT - 100, 120, 50)
BANK_BTN = pygame.Rect(WIDTH//2 + 20, HEIGHT - 100, 120, 50)
NEXT_BTN = pygame.Rect(WIDTH//2 - 60, HEIGHT - 160, 120, 50)

# --- Scoring setup ---
rules = ScoringRules()
rules.add_rule(ThreeOfAKind(1, 1000))
rules.add_rule(ThreeOfAKind(2, 200))
rules.add_rule(ThreeOfAKind(3, 300))
rules.add_rule(ThreeOfAKind(4, 400))
rules.add_rule(ThreeOfAKind(5, 500))
rules.add_rule(ThreeOfAKind(6, 600))
rules.add_rule(SingleValue(1, 100))
rules.add_rule(SingleValue(5, 50))
rules.add_rule(Straight6(1500))

# --- Game state ---
dice = [Die(random.randint(1, 6), 100 + i * (DICE_SIZE + MARGIN), HEIGHT // 2 - DICE_SIZE // 2) for i in range(6)]
turn_score = 0
current_roll_score = 0
total_score = 0
message = "Click ROLL to start!"
gamestate = GameState.START

# --- Helpers ---
def roll_dice():
    for d in dice:
        if not d.held:
            d.value = random.randint(1, 6)
            d.selected = False

def calculate_score_from_dice(dice_list):
    active = [d.value for d in dice_list if d.held or d.selected]
    if not active:
        return 0, []
    return rules.evaluate(active)

def check_farkle():
    """Check unheld dice for scoring."""
    unheld = [d for d in dice if not d.held]
    if not unheld:
        return False
    values = [d.value for d in unheld]
    score, _ = rules.evaluate(values)
    return score == 0

def all_dice_held():
    return all(d.held for d in dice)

def hot_dice_reset():
    global message
    for d in dice:
        d.reset()
        d.value = random.randint(1, 6)
    message = "HOT DICE! You can roll all 6 dice again!"
    mark_scoring_dice()

def reset_turn():
    global turn_score, gamestate, message
    for d in dice:
        d.reset()
        d.value = random.randint(1, 6)
    turn_score = 0
    gamestate = GameState.START
    message = "Click ROLL to start!"
    mark_scoring_dice()

def can_roll_again():
    return gamestate == GameState.START or any(d.held for d in dice)

def mark_scoring_dice():
    """Mark which unheld dice are part of a scoring combo."""
    for d in dice:
        d.scoring_eligible = False
    unheld = [d for d in dice if not d.held]
    if not unheld:
        return
    values = [d.value for d in unheld]
    score, contributing = rules.evaluate(values)
    for i in contributing:
        unheld[i].scoring_eligible = True

# --- Main loop ---
running = True
while running:
    screen.fill((40, 120, 40))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            # --- Click on dice ---
            for d in dice:
                if gamestate == GameState.ROLLING and d.rect().collidepoint(mx, my):
                    if not d.held and d.scoring_eligible:
                        d.toggle_select()
                        current_roll_score, _ = calculate_score_from_dice(dice)

            # --- ROLL button ---
            if ROLL_BTN.collidepoint(mx, my) and gamestate in (GameState.START, GameState.ROLLING):
                # First, convert all selected dice to held
                any_selected = False
                for d in dice:
                    if d.selected:
                        d.hold()
                        any_selected = True

                # Check if we can roll again
                if not can_roll_again():
                    message = "You must hold at least one scoring die!"
                else:
                    if gamestate == GameState.START:
                        gamestate = GameState.ROLLING

                    # Add this roll's score to the persistent turn score
                    turn_score += current_roll_score
                    current_roll_score = 0

                    # --- Hot Dice handling ---
                    if all_dice_held():
                        hot_dice_reset()
                        message = "HOT DICE! Roll all 6 again!"
                    else:
                        roll_dice()

                    # Refresh scoring eligibility
                    mark_scoring_dice()

                    # Check for Farkle
                    if check_farkle():
                        gamestate = GameState.FARKLE
                        message = "Farkle! You lose this turn's points."
                        turn_score = 0



            # --- BANK button ---
            if BANK_BTN.collidepoint(mx, my) and gamestate == GameState.ROLLING and (turn_score + current_roll_score) > 0:
                total_score += turn_score + current_roll_score
                gamestate = GameState.BANKED
                message = f"Banked {turn_score} points! Total: {total_score}"

            # --- NEXT TURN button ---
            if NEXT_BTN.collidepoint(mx, my) and gamestate in (GameState.FARKLE, GameState.BANKED):
                reset_turn()

    # --- Draw dice ---
    if gamestate in (GameState.ROLLING, GameState.FARKLE, GameState.BANKED):
        for d in dice:
            d.draw(screen)

    # --- Buttons ---
    pygame.draw.rect(screen, (250, 200, 50), ROLL_BTN, border_radius=10)
    pygame.draw.rect(screen, (100, 200, 100), BANK_BTN, border_radius=10)
    screen.blit(font.render("ROLL", True, (0, 0, 0)), (ROLL_BTN.x + 30, ROLL_BTN.y + 10))
    screen.blit(font.render("BANK", True, (0, 0, 0)), (BANK_BTN.x + 30, BANK_BTN.y + 10))

    if gamestate in (GameState.FARKLE, GameState.BANKED):
        pygame.draw.rect(screen, (200, 50, 50), NEXT_BTN, border_radius=10)
        screen.blit(font.render("Next Turn", True, (255, 255, 255)), (NEXT_BTN.x + 10, NEXT_BTN.y + 10))

    # --- Scores & messages ---
    screen.blit(font.render(message, True, (255, 255, 255)), (80, 60))
    screen.blit(font.render(f"Turn Score: {turn_score + current_roll_score}", True, (255, 255, 255)), (80, 100))
    screen.blit(font.render(f"Total Score: {total_score}", True, (255, 255, 255)), (80, 130))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
