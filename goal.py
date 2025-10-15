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
        # Unified Score object (lazy created when first needed)
        self._pending_score = None  # type: ignore
        # Layout cache (updated by draw())
        self._last_rect = None  # type: ignore[assignment]
        self._last_lines = None  # type: ignore[assignment]

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
                        rk = event.get("rule_key")
                        if raw > 0 and not self.is_fulfilled():
                            self.pending_raw += raw
                            if rk:
                                try:
                                    from score_types import Score
                                    if self._pending_score is None:
                                        self._pending_score = Score()
                                    self._pending_score.ensure_part(rk, raw)
                                except Exception:
                                    pass
                except Exception:
                    pass
        elif et == GameEventType.BANK:
            # On BANK: request scoring application instead of applying directly.
            if self.pending_raw > 0 and not self.is_fulfilled():
                from game_event import GameEvent as GE, GameEventType as GET
                # Build Score object if not already built
                score_obj = self._pending_score
                if score_obj is None:
                    try:
                        from score_types import Score
                        score_obj = Score()
                        self._pending_score = score_obj
                    except Exception:
                        score_obj = None
                payload = {"goal": self, "pending_raw": self.pending_raw}
                if score_obj is not None:
                    try:
                        payload["score"] = score_obj.to_dict()
                    except Exception:
                        pass
                self.game.event_listener.publish(GE(GET.SCORE_APPLY_REQUEST, payload=payload))
            else:
                # Nothing pending; just ensure cleared
                self.pending_raw = 0
                self._pending_score = None
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
                self._pending_score = None
        elif et == GameEventType.FARKLE:
            # Lose pending points for the turn
            self.pending_raw = 0
            self._pending_score = None
        # Other events (progress, fulfilled) currently ignored for animation hooks.

    def draw(self, surface):  # type: ignore[override]
        if not self.game:
            return
        # Renderer previously handled layout; we approximate with same logic values.
        g = self.game
        from settings import WIDTH, GOAL_PADDING, GOAL_LINE_SPACING, GOAL_WIDTH
        # Basic horizontal layout based on index
        goals = g.level_state.goals
        try:
            idx = goals.index(self)
        except ValueError:
            return
        total_goals = len(goals)
        spacing = 16
        left_x = 80
        right_margin = 40
        available_width = WIDTH - left_x - right_margin - (spacing * (total_goals - 1))
        per_box_width = min(GOAL_WIDTH, int(available_width / total_goals))
        per_box_width = max(140, per_box_width)
        used_width = per_box_width * total_goals + spacing * (total_goals - 1)
        start_x = left_x + (available_width - used_width) // 2 if used_width < available_width else left_x
        x = start_x + idx * (per_box_width + spacing)
        # Compute dynamic text lines similarly to renderer logic
        base_remaining = self.get_remaining()
        pending_raw = getattr(self, 'pending_raw', 0)
        if self.is_fulfilled():
            remaining_text = "Done"
        else:
            if pending_raw > 0:
                # Use game's preview helper for projected adjusted pending value
                try:
                    projected = g.compute_goal_pending_final(self)
                except Exception:
                    projected = pending_raw
                show_after = max(0, base_remaining - projected)
                remaining_text = f"Rem: {base_remaining} (pending {projected})"
            else:
                remaining_text = f"Rem: {base_remaining}"
        desc = g.level.description if idx == 0 else ""
        lines_out = self.build_lines(g.small_font, per_box_width, remaining_text, desc, GOAL_PADDING, GOAL_LINE_SPACING)
        box_height = self.compute_box_height(g.small_font, lines_out, GOAL_PADDING, GOAL_LINE_SPACING)
        panel_y = 90
        box_rect = pygame.Rect(x, panel_y, per_box_width, box_height)
        self._last_rect = box_rect
        self._last_lines = lines_out
        from settings import (
            GOAL_BG_MANDATORY, GOAL_BG_MANDATORY_DONE, GOAL_BG_OPTIONAL, GOAL_BG_OPTIONAL_DONE,
            GOAL_BORDER_ACTIVE, GOAL_TEXT
        )
        if self.mandatory:
            bg = GOAL_BG_MANDATORY_DONE if self.is_fulfilled() else GOAL_BG_MANDATORY
        else:
            bg = GOAL_BG_OPTIONAL_DONE if self.is_fulfilled() else GOAL_BG_OPTIONAL
        pygame.draw.rect(surface, bg, box_rect, border_radius=10)
        if g.active_goal_index == idx:
            pygame.draw.rect(surface, GOAL_BORDER_ACTIVE, box_rect, width=3, border_radius=10)
        self.draw_into(surface, box_rect, g.small_font, lines_out, GOAL_PADDING, GOAL_LINE_SPACING, GOAL_TEXT)
