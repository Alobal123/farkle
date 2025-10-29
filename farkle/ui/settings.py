"""Central settings and UI constants for Farkle game."""
import pygame

WIDTH, HEIGHT = 1200, 700
DICE_SIZE = 105
MARGIN = 20

# === COLOR PALETTE ===

# Background
BG_COLOR = (22, 38, 46)

# Button colors
BTN_ROLL_COLOR = (180, 140, 60)
BTN_LOCK_COLOR_DISABLED = (70, 70, 90)
BTN_LOCK_COLOR_ENABLED = (140, 120, 200)
BTN_BANK_COLOR = (60, 120, 80)

# Tooltip colors
TOOLTIP_DELAY_MS = 350  # base hover delay before displaying tooltip (non-buttons)
TOOLTIP_BUTTON_DELAY_MS = 1200  # longer delay for buttons specifically (original value restored)
TOOLTIP_BG_COLOR = (30, 45, 55)
TOOLTIP_BORDER_COLOR = (120, 160, 190)
TOOLTIP_TEXT_COLOR = (235, 235, 240)

# Text colors
TEXT_PRIMARY = (235, 225, 210)
TEXT_ACCENT = (255, 170, 80)
TEXT_MUTED = (160, 170, 165)
TEXT_WHITE = (255, 255, 255)
TEXT_LIGHT = (250, 250, 250)
TEXT_MEDIUM_LIGHT = (240, 240, 240)
TEXT_SLIGHTLY_MUTED = (230, 235, 240)
TEXT_VERY_LIGHT = (230, 230, 235)
TEXT_INFO = (190, 200, 210)

# Goal colors
GOAL_BG_DISASTER = (80, 32, 24)
GOAL_BG_DISASTER_DONE = (28, 92, 54)
GOAL_BG_PETITION = (32, 40, 96)
GOAL_BG_PETITION_DONE = (40, 100, 140)
GOAL_BORDER_ACTIVE = (255, 200, 120)
GOAL_TEXT = (240, 235, 225)
GOAL_PADDING = 8
GOAL_WIDTH = 240
GOAL_LINE_SPACING = 4

# HUD/Panel colors
HUD_BG = (40, 55, 70)
HUD_BORDER = (90, 140, 180)
PANEL_BG_DARK = (40, 55, 70)
PANEL_BORDER_LIGHT = (90, 140, 180)

# Help icon colors
HELP_ICON_BG = (60, 90, 120)
HELP_ICON_BORDER = (140, 190, 230)

# Choice window / card colors
CARD_BG_NORMAL = (65, 90, 120)
CARD_BG_SELECTED = (85, 110, 150)
CARD_BG_DISABLED = (45, 55, 65)
CARD_BORDER_NORMAL = (120, 170, 210)
CARD_BORDER_SELECTED = (180, 220, 255)
CARD_GLOW_FILL = (100, 150, 255)
CARD_GLOW_BORDER = (120, 180, 255)

# Relic/shop specific colors
RELIC_COST_AFFORDABLE = (230, 210, 100)
RELIC_COST_UNAFFORDABLE = (180, 100, 100)
RELIC_EFFECT_TEXT = (210, 210, 210)

# God panel colors
GOD_LORE_TEXT = (180, 200, 220)

# Level display colors
LEVEL_TEXT_COLOR = (180, 220, 255)

# Button text colors for choice windows
CHOICE_BTN_TEXT_ENABLED = (0, 0, 0)
CHOICE_BTN_TEXT_DISABLED = (100, 100, 100)
CHOICE_BTN_TEXT_VERY_DISABLED = (120, 120, 120)

# Choice window action button colors
CHOICE_CONFIRM_BTN_ENABLED = (80, 200, 110)
CHOICE_CONFIRM_BTN_DISABLED = (60, 80, 90)
CHOICE_SKIP_BTN = (180, 80, 60)
CHOICE_SELECT_BTN_ENABLED = (80, 200, 110)
CHOICE_SELECT_BTN_DISABLED = (60, 70, 80)

# Choice window panel colors
CHOICE_PANEL_BG = (40, 60, 80)
CHOICE_PANEL_BORDER = (80, 110, 140)
CHOICE_ICON_BG = (50, 70, 95)
CHOICE_MINIMIZE_BTN_BG = (80, 110, 140)
CHOICE_MINIMIZE_BTN_BORDER = (140, 180, 220)

# Generic UI colors
TEXT_HINT = (180, 180, 180)
TEXT_DISABLED_NAME = (140, 140, 140)

# Dice colors
DICE_SELECTED = (80, 150, 250)  # Blue color when dice selected for banking
DICE_HELD = (200, 80, 80)  # Red color when dice are held/locked
DICE_NORMAL = (230, 230, 230)  # Normal dice color
DICE_TARGET_SELECTION = (80, 150, 250)  # Color for ability target selection (matches banking selection)

# Button rectangles (created once; expect pygame.init before import)
ROLL_BTN = pygame.Rect(WIDTH//2 - 130, HEIGHT - 120, 120, 50)
BANK_BTN = pygame.Rect(WIDTH//2 + 10, HEIGHT - 120, 120, 50)
NEXT_BTN = pygame.Rect(WIDTH//2 - 60, HEIGHT - 240, 120, 50)
# Ability / utility buttons (expandable). Place to left of ROLL.
REROLL_BTN = pygame.Rect(WIDTH//2 - 80, HEIGHT - 70, 160, 40)
