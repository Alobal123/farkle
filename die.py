import pygame

DICE_SIZE = 80

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

        # Dim non-scoring dice
        if not self.held and not self.scoring_eligible:
            surf.set_alpha(130)

        # Draw pips
        pip_positions = {
            1: [(0.5, 0.5)],
            2: [(0.25, 0.25), (0.75, 0.75)],
            3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
            4: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)],
            5: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75), (0.5, 0.5)],
            6: [(0.25, 0.25), (0.25, 0.5), (0.25, 0.75),
                (0.75, 0.25), (0.75, 0.5), (0.75, 0.75)],
        }
        for px, py in pip_positions[self.value]:
            pygame.draw.circle(surf, (0, 0, 0),
                               (px * DICE_SIZE, py * DICE_SIZE), 7)
        surface.blit(surf, (self.x, self.y))
