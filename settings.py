"""Central settings and UI constants for Farkle game."""
import pygame

WIDTH, HEIGHT = 800, 600
DICE_SIZE = 80
MARGIN = 20

BG_COLOR = (22, 38, 46)
BTN_ROLL_COLOR = (180, 140, 60)
BTN_LOCK_COLOR_DISABLED = (70, 70, 90)
BTN_LOCK_COLOR_ENABLED = (140, 120, 200)
BTN_BANK_COLOR = (60, 120, 80)
TOOLTIP_DELAY_MS = 350  # base hover delay before displaying tooltip (non-buttons)
TOOLTIP_BUTTON_DELAY_MS = 1200  # longer delay for buttons specifically (original value restored)
TOOLTIP_BG_COLOR = (30, 45, 55)
TOOLTIP_BORDER_COLOR = (120, 160, 190)
TOOLTIP_TEXT_COLOR = (235, 235, 240)
TEXT_PRIMARY = (235, 225, 210)
TEXT_ACCENT = (255, 170, 80)
TEXT_MUTED = (160, 170, 165)
GOAL_BG_MANDATORY = (80, 32, 24)
GOAL_BG_MANDATORY_DONE = (28, 92, 54)
GOAL_BG_OPTIONAL = (32, 40, 96)
GOAL_BG_OPTIONAL_DONE = (40, 100, 140)
GOAL_BORDER_ACTIVE = (255, 200, 120)
GOAL_TEXT = (240, 235, 225)
GOAL_PADDING = 8
GOAL_WIDTH = 240
GOAL_LINE_SPACING = 4

# Button rectangles (created once; expect pygame.init before import)
ROLL_BTN = pygame.Rect(WIDTH//2 - 140, HEIGHT - 100, 120, 50)
BANK_BTN = pygame.Rect(WIDTH//2 + 20, HEIGHT - 100, 120, 50)
NEXT_BTN = pygame.Rect(WIDTH//2 - 60, HEIGHT - 160, 120, 50)
# Ability / utility buttons (expandable). Place to left of ROLL.
REROLL_BTN = pygame.Rect(WIDTH//2 - 340, HEIGHT - 100, 120, 50)
