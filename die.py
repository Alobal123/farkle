import pygame

DICE_SIZE = 80

# Precomputed pip layout (fractional positions within die square)
PIP_POSITIONS = {
    1: [(0.5, 0.5)],
    2: [(0.25, 0.25), (0.75, 0.75)],
    3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
    4: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)],
    5: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75), (0.5, 0.5)],
    6: [(0.25, 0.25), (0.25, 0.5), (0.25, 0.75), (0.75, 0.25), (0.75, 0.5), (0.75, 0.75)],
}

# Simple cache for rendered die surfaces keyed by (value, held, selected, scoring_eligible)
_die_surface_cache: dict[tuple[int,bool,bool,bool], pygame.Surface] = {}

class Die:
    def __init__(self, value, x, y):
        self.value = value
        self.x = x
        self.y = y
        self.held = False
        self.selected = False
        self.scoring_eligible = False

    def rect(self):
        return pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)

    def reset(self):
        self.held = False
        self.selected = False
        self.scoring_eligible = False

    def hold(self):
        self.held = True
        self.selected = False

    def toggle_select(self):
        self.selected = not self.selected

    def draw(self, surface):
        """Blit this die to surface using cached rendered surface keyed by its state."""
        key = (self.value, self.held, self.selected, self.scoring_eligible)
        cached = _die_surface_cache.get(key)
        if cached is None:
            # Color based on state
            if self.held:
                color = (200, 80, 80)  # red for held
            elif self.selected:
                color = (80, 150, 250)  # blue for selected this roll
            else:
                color = (230, 230, 230)  # white
            surf = pygame.Surface((DICE_SIZE, DICE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surf, color, surf.get_rect(), border_radius=8)
            pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 3, border_radius=8)
            if not self.held and not self.scoring_eligible:
                surf.set_alpha(130)
            for px, py in PIP_POSITIONS[self.value]:
                pygame.draw.circle(surf, (0, 0, 0), (px * DICE_SIZE, py * DICE_SIZE), 7)
            _die_surface_cache[key] = surf
            cached = surf
        surface.blit(cached, (self.x, self.y))
