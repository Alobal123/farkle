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
DICE_BORDER = (0, 0, 0)  # Black border for dice
DICE_PIPS = (0, 0, 0)  # Black pips on dice

# Progress bar colors
PROGRESS_BAR_TRACK = (50, 55, 60)  # Dark gray background track
PROGRESS_BAR_APPLIED = (70, 180, 110)  # Green for applied/completed progress
PROGRESS_BAR_PENDING = (200, 150, 60)  # Orange for pending progress
PROGRESS_BAR_PREVIEW = (110, 140, 220)  # Blue for preview/projected progress

# Goal summary text colors
GOAL_SUMMARY_TEXT = (230, 230, 228)  # Light gray for progress text
GOAL_REWARD_FAITH = (240, 230, 140)  # Golden yellow for faith rewards

# Category colors (petitions) - vibrant when active
CATEGORY_NATURE = ((60, 120, 60), (80, 160, 80))  # Green
CATEGORY_WARFARE = ((140, 50, 50), (180, 70, 70))  # Red
CATEGORY_SPIRIT = ((90, 70, 140), (120, 100, 180))  # Purple
CATEGORY_COMMERCE = ((160, 120, 40), (200, 150, 60))  # Gold/Yellow
CATEGORY_DEFAULT = ((80, 85, 90), (100, 105, 110))  # Neutral gray

# Category colors (fulfilled/done) - darker and desaturated
CATEGORY_NATURE_DONE = ((40, 70, 40), (50, 90, 50))
CATEGORY_WARFARE_DONE = ((80, 35, 35), (100, 50, 50))
CATEGORY_SPIRIT_DONE = ((50, 40, 80), (70, 60, 110))
CATEGORY_COMMERCE_DONE = ((90, 70, 30), (120, 95, 45))
CATEGORY_DEFAULT_DONE = ((60, 65, 70), (80, 85, 90))

# Game over screen colors
GAMEOVER_VICTORY_COLOR = (100, 220, 100)  # Green for victory
GAMEOVER_DEFEAT_COLOR = (220, 100, 100)  # Red for defeat
GAMEOVER_GOLD_STAT = (255, 215, 0)  # Gold color for gold stats
GAMEOVER_FARKLE_STAT = (220, 100, 100)  # Red for farkle stats
GAMEOVER_SCORE_STAT = (150, 200, 255)  # Blue for score stats
GAMEOVER_HIGHEST_STAT = (200, 150, 255)  # Purple for highest score
GAMEOVER_GENERAL_STAT = (180, 180, 180)  # Gray for general stats
GAMEOVER_BUTTON_COLOR = (80, 120, 160)  # Button normal color
GAMEOVER_BUTTON_HOVER = (100, 150, 200)  # Button hover color
GAMEOVER_BUTTON_BORDER = (200, 200, 200)  # Button border
GAMEOVER_HINT_TEXT = (150, 150, 150)  # Hint text color

# Font sizes
FONT_SIZE_TITLE = 60
FONT_SIZE_SUBTITLE = 32
FONT_SIZE_BUTTON = 36
FONT_SIZE_STATS = 20
FONT_SIZE_SMALL = 22
FONT_SIZE_HINT = 20

# Border radius values
BORDER_RADIUS_DICE = 8
BORDER_RADIUS_GOAL = 10
BORDER_RADIUS_BUTTON = 6
BORDER_RADIUS_HUD = 8
BORDER_RADIUS_CARD = 8
BORDER_RADIUS_PANEL = 12
BORDER_RADIUS_MINIMIZE = 4
BORDER_RADIUS_PROGRESS_BAR = 4

# Border widths
BORDER_WIDTH_DICE = 3
BORDER_WIDTH_GOAL_ACTIVE = 3
BORDER_WIDTH_TARGET_SELECTION = 4
BORDER_WIDTH_HUD = 2
BORDER_WIDTH_CARD = 2
BORDER_WIDTH_PANEL = 3
BORDER_WIDTH_MINIMIZE = 1
BORDER_WIDTH_GOD_NORMAL = 2
BORDER_WIDTH_GOD_SELECTED = 4

# Layout dimensions
CARD_WIDTH = 220
ICON_WIDTH = 180
BUTTON_WIDTH_CHOICE = 120
SHOP_PANEL_WIDTH = 600
BUTTON_WIDTH_MENU = 300
BUTTON_HEIGHT_MENU = 80

# Spacing constants
CONTENT_SPACING = 8
BAR_MARGIN = 6
BAR_HEIGHT = 14

# Dice rendering
DICE_PIP_RADIUS_RATIO = 0.07  # Pips are 7% of die size

# Button rectangles (created once; expect pygame.init before import)
ROLL_BTN = pygame.Rect(WIDTH//2 - 130, HEIGHT - 120, 120, 50)
BANK_BTN = pygame.Rect(WIDTH//2 + 10, HEIGHT - 120, 120, 50)
NEXT_BTN = pygame.Rect(WIDTH//2 - 60, HEIGHT - 240, 120, 50)
# Ability / utility buttons (expandable). Place to left of ROLL.
REROLL_BTN = pygame.Rect(WIDTH//2 - 80, HEIGHT - 70, 160, 40)
