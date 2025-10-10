import pygame

class Goal:
    def __init__(self, target_score: int, name: str = "", mandatory: bool = True, reward_gold: int = 0):
        self.target_score = target_score
        self.remaining = target_score
        self.name = name or "Goal"
        self.mandatory = mandatory
        # Reward system (future-proof for other reward types). For now only gold coins.
        self.reward_gold = reward_gold
        self.reward_claimed = False

    # Core logic
    def subtract(self, points: int):
        self.remaining = max(0, self.remaining - points)

    def is_fulfilled(self) -> bool:
        return self.remaining == 0

    def claim_reward(self) -> int:
        """Return gold reward if goal is fulfilled and not yet claimed; mark claimed."""
        if self.is_fulfilled() and not self.reward_claimed and self.reward_gold > 0:
            self.reward_claimed = True
            return self.reward_gold
        return 0

    def get_remaining(self) -> int:
        return self.remaining

    # Rendering helpers (decoupled from Game specifics but reusable)
    @staticmethod
    def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines

    def build_lines(self, font: pygame.font.Font, box_width: int, remaining_text: str, desc: str | None, padding: int, line_spacing: int) -> list[str]:
        tag = "M" if self.mandatory else "O"
        combined = f"{self.name} [{tag}]\n{remaining_text}"
        if desc:
            combined += f"\n{desc}"
        lines_out: list[str] = []
        content_width = box_width - 2 * padding
        for raw_line in combined.split("\n"):
            wrapped = self.wrap_text(font, raw_line, content_width)
            lines_out.extend(wrapped)
        return lines_out

    def compute_box_height(self, font: pygame.font.Font, lines: list[str], padding: int, line_spacing: int) -> int:
        return padding * 2 + len(lines) * (font.get_height() + line_spacing) - line_spacing

    def draw_into(self, surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font, lines: list[str], padding: int, line_spacing: int, text_color: tuple[int,int,int]):
        y_line = rect.y + padding
        for ln in lines:
            surface.blit(font.render(ln, True, text_color), (rect.x + padding, y_line))
            y_line += font.get_height() + line_spacing
