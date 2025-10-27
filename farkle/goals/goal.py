import pygame
from farkle.core.game_object import GameObject
from farkle.core.game_event import GameEvent, GameEventType
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from farkle.game import Game

class Goal(GameObject):
    def __init__(self, target_score: int, name: str = "", is_disaster: bool = True, reward_gold: int = 0, flavor: str = "", category: str = "", persona: str = "", reward_income: int = 0, reward_blessing: str = ""):
        super().__init__(name or "Goal")
        self.target_score = target_score
        self.remaining = target_score
        self.name = name or "Goal"
        self.is_disaster = is_disaster
        self.flavor = flavor
        self.category = category  # Category for color coding: nature, warfare, spirit, commerce
        self.persona = persona  # Persona for reward type: farmer, merchant, nobleman, etc.
        # Reward system (supports gold, income, and blessing rewards)
        self.reward_gold = reward_gold
        self.reward_income = reward_income
        self.reward_blessing = reward_blessing  # Type of blessing to grant (e.g., "double_score")
        self.reward_claimed = False
        self.game: Optional["Game"] = None  # back reference assigned when subscribed
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

    def claim_reward(self) -> tuple[int, int, str]:
        """Return (gold_reward, income_reward, blessing_type) if goal is fulfilled and not yet claimed; mark claimed.
        
        Returns:
            tuple[int, int, str]: (gold_amount, income_amount, blessing_type)
        """
        if self.is_fulfilled() and not self.reward_claimed and (self.reward_gold > 0 or self.reward_income > 0 or self.reward_blessing):
            self.reward_claimed = True
            return (self.reward_gold, self.reward_income, self.reward_blessing)
        return (0, 0, "")

    def get_remaining(self) -> int:
        return self.remaining

    # Projection helper for UI/logic: ask scoring manager directly.
    def projected_pending(self) -> int:
        try:
            sm = getattr(self.game, 'scoring_manager', None)
            if sm:
                return sm.project_goal_pending(self)
        except Exception:
            pass
        return int(getattr(self, 'pending_raw', 0) or 0)

    # Rendering helpers (decoupled from Game specifics but reusable)
    @staticmethod
    def get_category_colors(category: str, is_fulfilled: bool) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Return (background_color, border_color) for a given category.
        
        Categories: nature, warfare, spirit, commerce
        Returns darker/desaturated colors when fulfilled.
        """
        # Base colors for each category (vibrant when active)
        category_colors = {
            'nature': ((60, 120, 60), (80, 160, 80)),      # Green
            'warfare': ((140, 50, 50), (180, 70, 70)),     # Red
            'spirit': ((90, 70, 140), (120, 100, 180)),    # Purple
            'commerce': ((160, 120, 40), (200, 150, 60)),  # Gold/Yellow
        }
        
        # Fulfilled (done) colors - darker and desaturated
        category_colors_done = {
            'nature': ((40, 70, 40), (50, 90, 50)),
            'warfare': ((80, 35, 35), (100, 50, 50)),
            'spirit': ((50, 40, 80), (70, 60, 110)),
            'commerce': ((90, 70, 30), (120, 95, 45)),
        }
        
        # Get colors based on category, default to neutral gray if unknown
        if is_fulfilled:
            bg, border = category_colors_done.get(category, ((60, 65, 70), (80, 85, 90)))
        else:
            bg, border = category_colors.get(category, ((80, 85, 90), (100, 105, 110)))
        
        return bg, border

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
        tag = "D" if self.is_disaster else "P"
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
                                    from farkle.scoring.score_types import Score
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
                from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                # Build Score object if not already built
                score_obj = self._pending_score
                if score_obj is None:
                    try:
                        from farkle.scoring.score_types import Score
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
                    from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                    self.game.event_listener.publish(GE(GET.GOAL_PROGRESS, payload={
                        "goal_name": self.name,
                        "delta": delta,
                        "remaining": self.remaining
                    }))
                    if self.is_fulfilled():
                        # Mark as fulfilled but don't publish event yet
                        # Store that we need to publish after TURN_END
                        self._fulfilled_this_turn = True
                        if self.game.level_state._all_disasters_fulfilled():
                            self.game.level_state.completed = True
                # Clear pending after application
                self.pending_raw = 0
                self._pending_score = None
        elif et == GameEventType.FARKLE:
            # No longer clears pending immediately. Pending points are retained until TURN_END
            # with a farkle-related reason. This supports future in-farkle recovery mechanics.
            pass
        elif et == GameEventType.TURN_END:
            # If a farkle is being finalized (player forfeits or rescue failed), ensure pending cleared.
            reason = event.get("reason")
            if reason in ("farkle", "farkle_forfeit"):
                self.pending_raw = 0
                self._pending_score = None
            
            # Publish deferred GOAL_FULFILLED events after turn ends
            if getattr(self, '_fulfilled_this_turn', False):
                from farkle.core.game_event import GameEvent as GE, GameEventType as GET
                self.game.event_listener.publish(GE(GET.GOAL_FULFILLED, payload={
                    "goal_name": self.name,
                    "goal": self,
                    "reward_gold": self.reward_gold
                }))
                self._fulfilled_this_turn = False
        # Other events (progress, fulfilled) currently ignored for animation hooks.

    def draw(self, surface):  # type: ignore[override]
        # Renderer previously handled layout; we approximate with same logic values.
        g = self.game
        from farkle.ui.settings import WIDTH, GOAL_PADDING, GOAL_LINE_SPACING, GOAL_WIDTH
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
        # Calculate dynamic progress values (applied, pending, preview)
        applied = self.target_score - base_remaining
        projected_pending = 0
        if not self.is_fulfilled() and pending_raw > 0:
            try:
                projected_pending = max(0, self.projected_pending())
            except Exception:
                projected_pending = pending_raw
        preview_add = 0
        try:
            if g.selection_is_single_combo() and g.any_scoring_selection():
                preview_tuple = g.selection_preview()
                if isinstance(preview_tuple, tuple) and len(preview_tuple) >= 3 and g.active_goal_index == goals.index(self):
                    preview_add = int(preview_tuple[2])
        except Exception:
            preview_add = 0
        # Build lines: only name/tag (description removed; now shown only via hover tooltip)
        tag = "D" if self.is_disaster else "P"
        header = f"{self.name} [{tag}]"
        content = header
        lines_out: list[str] = []
        for raw_line in content.split("\n"):
            wrapped = self.wrap_text(g.small_font, raw_line, per_box_width - 2 * GOAL_PADDING)
            lines_out.extend(wrapped)
        # Reserve space for progress bar at bottom
        bar_reserved_height = 20
        box_height = GOAL_PADDING * 2 + len(lines_out) * (g.small_font.get_height() + GOAL_LINE_SPACING) - GOAL_LINE_SPACING + bar_reserved_height
        panel_y = 90
        box_rect = pygame.Rect(x, panel_y, per_box_width, box_height)
        self._last_rect = box_rect
        self._last_lines = lines_out
        from farkle.ui.settings import GOAL_BORDER_ACTIVE, GOAL_TEXT
        
        # Use category-based colors
        bg, border = self.get_category_colors(self.category, self.is_fulfilled())
        
        pygame.draw.rect(surface, bg, box_rect, border_radius=10)
        if g.active_goal_index == idx:
            pygame.draw.rect(surface, GOAL_BORDER_ACTIVE, box_rect, width=3, border_radius=10)
        # Draw text lines first (top region)
        y_line = box_rect.y + GOAL_PADDING
        for ln in lines_out:
            surface.blit(g.small_font.render(ln, True, GOAL_TEXT), (box_rect.x + GOAL_PADDING, y_line))
            y_line += g.small_font.get_height() + GOAL_LINE_SPACING
        # Progress bar at bottom
        bar_margin = 6
        bar_height = 14
        bar_x = box_rect.x + bar_margin
        bar_y = box_rect.bottom - bar_margin - bar_height
        bar_width = box_rect.width - bar_margin * 2
        # Background track
        track_color = (50, 55, 60)
        pygame.draw.rect(surface, track_color, pygame.Rect(bar_x, bar_y, bar_width, bar_height), border_radius=4)
        # Segment calculations (avoid division by zero)
        total = max(1, self.target_score)
        applied_w = int(bar_width * applied / total)
        pending_w = int(bar_width * projected_pending / total)
        preview_w = int(bar_width * preview_add / total)
        # Clamp cumulative widths to bar_width
        # If applied exceeds bar, cap applied and zero others
        if applied_w > bar_width:
            applied_w = bar_width
            pending_w = 0
            preview_w = 0
        else:
            # Reduce pending if it would overflow
            if applied_w + pending_w > bar_width:
                pending_w = max(0, bar_width - applied_w)
                preview_w = 0
            # Reduce preview if it would overflow
            if applied_w + pending_w + preview_w > bar_width:
                preview_w = max(0, bar_width - applied_w - pending_w)
        # Store debug values for tests
        self._last_bar_widths = {
            'applied': applied_w,
            'pending': pending_w,
            'preview': preview_w,
            'total': bar_width
        }
        # Colors (could move to settings if reused)
        applied_color = (70, 180, 110)
        pending_color = (200, 150, 60)
        preview_color = (110, 140, 220)
        # Draw applied segment
        if applied_w > 0:
            pygame.draw.rect(surface, applied_color, pygame.Rect(bar_x, bar_y, applied_w, bar_height), border_radius=4)
        # Draw pending segment (stacks after applied)
        if pending_w > 0:
            pygame.draw.rect(surface, pending_color, pygame.Rect(bar_x + applied_w, bar_y, pending_w, bar_height), border_radius=0)
        # Draw preview segment (after applied+pending)
        if preview_w > 0:
            pygame.draw.rect(surface, preview_color, pygame.Rect(bar_x + applied_w + pending_w, bar_y, preview_w, bar_height), border_radius=0)
        # Text overlay inside bar (compact summary)
        summary = f"{applied}/{self.target_score}"
        if projected_pending:
            summary += f"+{projected_pending}"
        if preview_add:
            summary += f"+{preview_add}"
        surface.blit(g.small_font.render(summary, True, (230,230,228)), (bar_x + 4, bar_y - 1))
