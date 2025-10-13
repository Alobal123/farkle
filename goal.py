import pygame
from game_object import GameObject
from game_event import GameEvent, GameEventType

class Goal(GameObject):
    def __init__(self, target_score: int, name: str = "", mandatory: bool = True, reward_gold: int = 0):
        super().__init__(name or "Goal")
        self.target_score = target_score
        self.remaining = target_score
        self.name = name or "Goal"
        self.mandatory = mandatory
        # Reward system (future-proof for other reward types). For now only gold coins.
        self.reward_gold = reward_gold
        self.reward_claimed = False
        self.game = None  # back reference assigned when subscribed
        # Pending raw points accumulated this turn (before multiplier & banking)
        self.pending_raw: int = 0

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

    def on_event(self, event: GameEvent) -> None:  # type: ignore[override]
        """React to scoring lifecycle events.

    Flow:
    - LOCK accumulates raw pending.
    - BANK applies (multiplied) pending and emits progress/fulfillment.
    - FARKLE discards pending.
        """
        if not self.game:
            return
        et = event.type
        if et == GameEventType.LOCK:
            idx = event.get("goal_index")
            if idx is not None:
                try:
                    if self.game.level_state.goals[idx] is self:
                        raw = int(event.get("points", 0))
                        if raw > 0 and not self.is_fulfilled():
                            self.pending_raw += raw
                except Exception:
                    pass
        elif et == GameEventType.BANK:
            # On BANK: request scoring application instead of applying directly.
            if self.pending_raw > 0 and not self.is_fulfilled():
                from game_event import GameEvent as GE, GameEventType as GET
                self.game.event_listener.publish(GE(GET.SCORE_APPLY_REQUEST, payload={
                    "goal": self,
                    "pending_raw": self.pending_raw
                }))
            else:
                # Nothing pending; just ensure cleared
                self.pending_raw = 0
        elif et == GameEventType.SCORE_APPLIED:
            # Player has computed adjusted score; payload includes goal reference
            target = event.get("goal")
            if target is self and not self.is_fulfilled():
                adjusted = int(event.get("adjusted", 0))
                if adjusted > 0 and self.pending_raw > 0:
                    before = self.remaining
                    self.subtract(adjusted)
                    delta = before - self.remaining
                    from game_event import GameEvent as GE, GameEventType as GET
                    self.game.event_listener.publish(GE(GET.GOAL_PROGRESS, payload={
                        "goal_name": self.name,
                        "delta": delta,
                        "remaining": self.remaining
                    }))
                    if self.is_fulfilled():
                        self.game.event_listener.publish(GE(GET.GOAL_FULFILLED, payload={
                            "goal_name": self.name,
                            "goal": self,
                            "reward_gold": self.reward_gold
                        }))
                        if self.game.level_state._all_mandatory_fulfilled():
                            self.game.level_state.completed = True
                # Clear pending after application
                self.pending_raw = 0
        elif et == GameEventType.FARKLE:
            # Lose pending points for the turn
            self.pending_raw = 0
        # Other events (progress, fulfilled) currently ignored for animation hooks.

    def draw(self, surface):  # type: ignore[override]
        # Drawing still handled by renderer; no direct sprite.
        return
