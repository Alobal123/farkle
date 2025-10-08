import pygame
import random
import sys
from game_state_enum import GameState

# --- Pygame setup ---
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Farkle - Push Your Luck")
font = pygame.font.SysFont("Arial", 26)
clock = pygame.time.Clock()

# --- Constants ---
DICE_SIZE = 80
MARGIN = 20
ROLL_BTN = pygame.Rect(WIDTH//2 - 140, HEIGHT - 100, 120, 50)
BANK_BTN = pygame.Rect(WIDTH//2 + 20, HEIGHT - 100, 120, 50)
NEXT_BTN = pygame.Rect(WIDTH//2 - 60, HEIGHT - 160, 120, 50)

# --- Game state ---
dice_values = [random.randint(1, 6) for _ in range(6)]
held = [False] * 6
turn_score = 0       # Total score for the current turn
current_roll_score = 0  # Score from this roll (held + selected dice)
total_score = 0
message = "Click ROLL to start!"
gamestate = GameState.START
# True if the die is newly selected this roll
selected = [False] * 6

# --- Dice drawing ---
def draw_die(value, held=False, newly_selected=False):
    surf = pygame.Surface((DICE_SIZE, DICE_SIZE))
    if held:
        color = (200, 80, 80)  # red for already held
    elif newly_selected:
        color = (80, 150, 250)  # blue for newly selected
    else:
        color = (230, 230, 230)  # white for unheld/unselected
    pygame.draw.rect(surf, color, surf.get_rect(), border_radius=8)
    pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 3, border_radius=8)

    # draw pips as before
    pip_positions = {
        1: [(0.5, 0.5)],
        2: [(0.25, 0.25), (0.75, 0.75)],
        3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
        4: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)],
        5: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75), (0.5, 0.5)],
        6: [(0.25, 0.25), (0.25, 0.5), (0.25, 0.75), (0.75, 0.25), (0.75, 0.5), (0.75, 0.75)],
    }
    for px, py in pip_positions[value]:
        pygame.draw.circle(surf, (0, 0, 0), (px * DICE_SIZE, py * DICE_SIZE), 7)
    return surf



def dice_score(value, count_same=1):
    """Return points for a single die (or multiples of the same number)."""
    score = 0
    # Triplets
    if count_same >= 3:
        if value == 1:
            score += 1000 * (2 ** (count_same - 3))
        else:
            score += value * 100 * (2 ** (count_same - 3))
        count_same -= 3
    # Singles
    if value == 1:
        score += count_same * 100
    elif value == 5:
        score += count_same * 50
    return score

def get_scoring_dice_indices():
    """Return list of indices of dice that are eligible to be held (contribute points)."""
    counts = {i: dice_values.count(i) for i in range(1, 7)}
    scoring_indices = []
    for i, val in enumerate(dice_values):
        if held[i]:
            continue  # already held
        # Check if this die or its triplet contributes points
        if val == 1 or val == 5:
            scoring_indices.append(i)
        elif counts[val] >= 3:
            scoring_indices.append(i)
    return scoring_indices


# --- Scoring ---
def calculate_score(dice):
    counts = {i: dice.count(i) for i in range(1, 7)}
    score = 0
    for num, count in counts.items():
        if count >= 3:
            if num == 1:
                score += 1000 * (2 ** (count - 3))
            else:
                score += num * 100 * (2 ** (count - 3))
            count -= 3
        if num == 1:
            score += count * 100
        elif num == 5:
            score += count * 50
    return score

# --- Dice rolling ---
def roll_dice():
    for i in range(6):
        if not held[i]:
            dice_values[i] = random.randint(1, 6)

def check_farkle():
    """Check only unheld dice for scoring."""
    unheld_dice = [dice_values[i] for i in range(6) if not held[i]]
    if not unheld_dice:
        return False
    return calculate_score(unheld_dice) == 0

def all_dice_held():
    return all(held)

def hot_dice_reset():
    global held, dice_values, selected, message
    held = [False] * 6        # all dice unlocked
    selected = [False] * 6    # clear current selections
    dice_values = [random.randint(1, 6) for _ in range(6)]
    message = "HOT DICE! You can roll all 6 dice again!"


def reset_turn():
    global held, dice_values, turn_score, gamestate, message
    held = [False] * 6
    dice_values = [random.randint(1, 6) for _ in range(6)]
    turn_score = 0
    gamestate = GameState.START
    message = "Click ROLL to start!"

def can_roll_again():
    """First roll always allowed; subsequent rolls require at least one die held."""
    return gamestate == GameState.START or any(held)

# --- Main loop ---
running = True
while running:
    screen.fill((40, 120, 40))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            # When player clicks a die
            for i in range(6):
                x = 100 + i * (DICE_SIZE + MARGIN)
                y = HEIGHT // 2 - DICE_SIZE // 2
                if pygame.Rect(x, y, DICE_SIZE, DICE_SIZE).collidepoint(mx, my):
                    if gamestate == GameState.ROLLING and not held[i]:
                        if i in get_scoring_dice_indices():
                            # Toggle selection
                            selected[i] = not selected[i]

                            # Update temporary turn score
                            current_roll_score = calculate_score(
                                [dice_values[i] for i in range(6) if held[i] or selected[i]]
                            )


            # --- Roll button ---
            if ROLL_BTN.collidepoint(mx, my) and gamestate in (GameState.START, GameState.ROLLING):

                for i in range(6):
                    if selected[i]:
                        held[i] = True
                        selected[i] = False  # reset selection for next roll


                if not can_roll_again():
                    message = "You must hold at least one scoring die!"
                else:
                    if gamestate == GameState.START:
                        gamestate = GameState.ROLLING

                    # --- Calculate score BEFORE hot dice reset ---
                    # Add this roll's score to the persistent turn score
                    turn_score += current_roll_score
                    current_roll_score = 0  # reset for next roll

                    for i in range(6):
                        if selected[i]:
                            held[i] = True
                            selected[i] = False

                    # --- Hot Dice: all dice held and scoring ---
                    if all_dice_held():
                        hot_dice_reset()  # resets held & selection, dice_values
                        message += " HOT DICE! Roll all 6 again."

                    # Roll unheld dice
                    roll_dice()

                    # Check Farkle on unheld dice
                    if check_farkle():
                        gamestate = GameState.FARKLE
                        message = "Farkle! You lose this turn's points."
                        turn_score = 0


            # --- Bank button ---
            if BANK_BTN.collidepoint(mx, my) and gamestate == GameState.ROLLING and turn_score + current_roll_score > 0:
                for i in range(6):
                    if selected[i]:
                        held[i] = True
                        selected[i] = False  # reset selection for next roll
                total_score += turn_score + current_roll_score
                message = f"Banked {turn_score} points! Total: {total_score}"
                gamestate = GameState.BANKED

            # --- Next Turn button ---
            if NEXT_BTN.collidepoint(mx, my) and gamestate in (GameState.FARKLE, GameState.BANKED):
                reset_turn()

    # --- Draw dice only if rolled ---
    if gamestate in (GameState.ROLLING, GameState.FARKLE, GameState.BANKED):
        for i, val in enumerate(dice_values):
            x = 100 + i * (DICE_SIZE + MARGIN)
            y = HEIGHT // 2 - DICE_SIZE // 2
            screen.blit(draw_die(
                val,
                held=held[i],
                newly_selected=selected[i]
            ), (x, y))

    # --- Draw buttons ---
    pygame.draw.rect(screen, (250, 200, 50), ROLL_BTN, border_radius=10)
    pygame.draw.rect(screen, (100, 200, 100), BANK_BTN, border_radius=10)
    screen.blit(font.render("ROLL", True, (0, 0, 0)), (ROLL_BTN.x + 30, ROLL_BTN.y + 10))
    screen.blit(font.render("BANK", True, (0, 0, 0)), (BANK_BTN.x + 30, BANK_BTN.y + 10))

    if gamestate in (GameState.FARKLE, GameState.BANKED):
        pygame.draw.rect(screen, (200, 50, 50), NEXT_BTN, border_radius=10)
        screen.blit(font.render("Next Turn", True, (255, 255, 255)), (NEXT_BTN.x + 10, NEXT_BTN.y + 10))

    # --- Draw messages & scores ---
    screen.blit(font.render(message, True, (255, 255, 255)), (80, 60))
    screen.blit(font.render(f"Turn Score: {turn_score + current_roll_score}", True, (255, 255, 255)), (80, 100))
    screen.blit(font.render(f"Total Score: {total_score}", True, (255, 255, 255)), (80, 130))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
