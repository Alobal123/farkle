import pygame, sys
from game_state_manager import GameStateManager
from scoring import (
    ScoringRules,
    SingleValue,
    ThreeOfAKind,
    FourOfAKind,
    FiveOfAKind,
    SixOfAKind,
    Straight6,
    Straight1to5,
    Straight2to6,
)
from die import Die
from dice_container import DiceContainer
from level import Level, LevelState
from player import Player
from game_event import GameEvent, GameEventType
from event_listener import EventListener
from actions import handle_lock as action_handle_lock, handle_roll as action_handle_roll, handle_bank as action_handle_bank, handle_next_turn as action_handle_next_turn
from input_controller import InputController
from renderer import GameRenderer
from settings import ROLL_BTN, LOCK_BTN, BANK_BTN, NEXT_BTN
from ui_objects import build_core_buttons, HelpIcon, RelicPanel, ShopOverlay, RulesOverlay
from game_object import GameObject
from relic_manager import RelicManager
from ability_manager import AbilityManager

class Game:
    def __init__(self, screen, font, clock, level: Level | None = None):
        self.screen = screen
        self.font = font
        # Small font for auxiliary text
        try:
            self.small_font = pygame.font.Font(None, 22)
        except Exception:
            self.small_font = font
        self.clock = clock
        # Use provided level or default prototype (multi-goal capable)
        self.level = level or Level.single(name="Invocation Rite", target_goal=300, max_turns=2, description="Basic ritual to avert a minor omen.")
        self.level_state = LevelState(self.level)
        self.active_goal_index: int = 0
        self.rules = ScoringRules()
        self._init_rules()
        self.state_manager = GameStateManager(on_change=self._on_state_change)
        # Dice container encapsulates all dice logic
        self.dice_container = DiceContainer(self)
        # Dynamic GameObjects (dice etc.) for unified rendering pipeline
        try:
            self.ui_dynamic = list(self.dice_container.dice)
        except Exception:
            self.ui_dynamic = []
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.level_index = 1
        # Track whether at least one scoring combo has been locked since the most recent roll
        self.locked_after_last_roll = False
        # Player meta progression container
        self.player = Player()
        self.player.game = self
        # Relic manager handles between-level shop & relic aggregation
        self.relic_manager = RelicManager(self)
        # Renderer handles all drawing/UI composition
        self.renderer = GameRenderer(self)
        # UI game objects (buttons) built after renderer/font ready
        self.ui_buttons = build_core_buttons(self)
        # Misc UI objects (help icon, overlays later)
        self.show_help = False
        self.ui_misc: list[GameObject] = [HelpIcon(10, self.screen.get_height() - 50, 40), RelicPanel(), ShopOverlay(), RulesOverlay(), self.player]
        for obj in self.ui_misc:
            obj.game = self  # type: ignore[attr-defined]
    # Legacy reroll tracking fields removed; ability manager owns reroll state.
        self.ability_manager = AbilityManager(self)
        # Event listener hub
        self.event_listener = EventListener()
        # Internal flag: when True we defer TURN_START emission (e.g., awaiting shop interaction after advancement)
        self._defer_turn_start = False
        # Subscribe player & goals
        self._subscribe_core_objects()
        # Subscribe relic manager
        self.event_listener.subscribe(self.relic_manager.on_event)
        # Input controller (handles REQUEST_* events)
        self.input_controller = InputController(self)
        self.event_listener.subscribe(self.input_controller.on_event)
        # Emit initial TURN_START for the very first turn
        try:
            self.begin_turn(initial=True)
        except Exception:
            pass
        # Subscribe game itself for auto progression
        self.event_listener.subscribe(self.on_event)
    # dice already initialized by container

    def _init_rules(self):
        # Base three-of-a-kind values
        three_kind_values = {
            1: 1000,
            2: 200,
            3: 300,
            4: 400,
            5: 500,
            6: 600,
        }
        for v, pts in three_kind_values.items():
            self.rules.add_rule(ThreeOfAKind(v, pts))
            self.rules.add_rule(FourOfAKind(v, pts))   # double three-kind value
            self.rules.add_rule(FiveOfAKind(v, pts))   # triple three-kind value
            self.rules.add_rule(SixOfAKind(v, pts))    # quadruple three-kind value
        self.rules.add_rule(SingleValue(1, 100))
        self.rules.add_rule(SingleValue(5, 50))
        self.rules.add_rule(Straight6(1500))
        # New 5-length partial straights
        self.rules.add_rule(Straight1to5(1000))
        self.rules.add_rule(Straight2to6(1000))

    # --- scoring preview helpers -------------------------------------------------
    def compute_goal_pending_final(self, goal) -> int:
        """Return projected final adjusted score for a goal's current pending_raw using unified preview pipeline."""
        pending_raw = int(getattr(goal, 'pending_raw', 0) or 0)
        if pending_raw <= 0:
            return 0
        try:
            score_obj = getattr(goal, '_pending_score', None)
            if score_obj is None:
                return pending_raw
            # Build parts list from cloned score for isolation
            clone = score_obj.clone()
            parts = [(p.rule_key, p.raw) for p in clone.parts]
            preview = self.compute_preview(parts, source="goal_pending")
            return int(preview.get('final_preview', pending_raw))
        except Exception:
            return pending_raw

    def compute_preview(self, parts: list[tuple[str,int]], source: str = "selection") -> dict:
        """Compute a preview Score object applying selective modifiers (via SCORE_PRE_MODIFIERS) and global multipliers.

        parts: list of (rule_key, raw)
        Returns dict with keys: parts (list of {rule_key, raw, adjusted}), total_raw, selective_effective,
        multiplier, final_preview, score (serialized full score dict) for potential future use.
        Emits SCORE_PREVIEW_REQUEST then SCORE_PREVIEW_COMPUTED for observers (non-mutating).
        """
        """Compute a preview Score object applying selective modifiers (via SCORE_PRE_MODIFIERS).

        Global multipliers have been removed from gameplay; preview's final equals selective.
        Returns a dict with: parts (list[rule_key, raw]), total_raw, selective_effective,
        multiplier (always 1.0), final_preview, score (serialized full score dict).
        """
        from game_event import GameEvent as GE, GameEventType as GET
        result: dict = {}
        try:
            from score_types import Score, ScorePart
            score_obj = Score()
            for rk, raw in parts:
                try:
                    score_obj.add_part(ScorePart(rule_key=rk, raw=int(raw)))
                except Exception:
                    pass
            # Fire preview request event (informational)
            try:
                self.event_listener.publish(GE(GET.SCORE_PREVIEW_REQUEST, payload={
                    "parts": [{"rule_key": rk, "raw": raw} for rk, raw in parts],
                    "source": source
                }))
            except Exception:
                pass
            # Apply selective modifiers by leveraging SCORE_PRE_MODIFIERS immediate hook
            try:
                self.event_listener.publish_immediate(GE(GET.SCORE_PRE_MODIFIERS, payload={
                    "score_obj": score_obj,
                    "preview": True,
                    "source": source
                }))
            except Exception:
                pass
            selective_effective = score_obj.total_effective
            # Global multipliers are not applied; final equals selective
            total_mult = 1.0
            final_preview = selective_effective
            score_dict = None
            try:
                score_dict = score_obj.to_dict()
            except Exception:
                score_dict = None
            result = {
                "parts": score_dict.get('parts') if score_dict else [{"rule_key": rk, "raw": raw} for rk, raw in parts],
                "total_raw": sum(raw for _,raw in parts),
                "selective_effective": selective_effective,
                "multiplier": total_mult,
                "final_preview": final_preview,
                "score": score_dict,
            }
            try:
                self.event_listener.publish(GE(GET.SCORE_PREVIEW_COMPUTED, payload=result | {"source": source}))
            except Exception:
                pass
            return result
        except Exception:
            return {"parts": [{"rule_key": rk, "raw": raw} for rk, raw in parts], "total_raw": sum(raw for _,raw in parts), "selective_effective": sum(raw for _,raw in parts), "multiplier": 1.0, "final_preview": sum(raw for _,raw in parts)}

    def reset_dice(self):
        self.dice_container.reset_all()
        # Refresh dynamic dice list to reflect new Die instances
        self.ui_dynamic = list(self.dice_container.dice)

    def _recreate_dice(self):
        """Recreate dice objects and clear selection/held state for a fresh turn or reset."""
        self.dice_container.reset_all()
        self.ui_dynamic = list(self.dice_container.dice)
        # Clear selection & eligibility flags explicitly
        for d in self.dice_container.dice:
            d.selected = False
            d.scoring_eligible = False
            d.held = False  # ensure not carried over
        self.locked_after_last_roll = False
        # Mark scoring dice for initial PRE_ROLL informational highlighting (if any)
        try:
            self.mark_scoring_dice()
        except Exception:
            pass

    def reset_game(self):
        # When called after win/lose we keep current level (already advanced on win)
        self._recreate_dice()
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.state_manager = GameStateManager(on_change=self._on_state_change)
        self.level_state.reset()
        self.active_goal_index = 0
        # Reset per-level ability uses
    # Ability manager reset handles reroll availability now.
        if hasattr(self, 'ability_manager'):
            self.ability_manager.reset_level()
        # pending scores moved into Goal.pending_raw; ensure cleared
        for g in self.level_state.goals:
            g.pending_raw = 0
        advancing = getattr(self, "_advancing_level", False)
        if advancing:
            # During advancement do NOT replace the event_listener (keeps queued events like LEVEL_GENERATED intact)
            try:
                from goal import Goal as _Goal
                # Remove old goal callbacks
                filtered = []
                for cb in list(getattr(self.event_listener, "_subs_all", [])):
                    bound_self = getattr(cb, "__self__", None)
                    if bound_self is not None and isinstance(bound_self, _Goal):
                        # remove
                        try:
                            self.event_listener.unsubscribe(cb)
                        except Exception:
                            pass
                    else:
                        filtered.append(cb)
                # Re-subscribe new goals with updated level_state
                for g in self.level_state.goals:
                    g.game = self  # type: ignore[attr-defined]
                    self.event_listener.subscribe(g.on_event)
                # Ensure game.on_event still subscribed
                if self.on_event not in getattr(self.event_listener, "_subs_all", []):
                    self.event_listener.subscribe(self.on_event)
            except Exception:
                pass
        else:
            # Non-advancement path: full reset including listener replacement (retain external subscribers)
            preserved_callbacks: list = []
            try:
                from goal import Goal as _Goal
                for cb in getattr(self.event_listener, "_subs_all", []):
                    bound_self = getattr(cb, "__self__", None)
                    if bound_self is None or not isinstance(bound_self, _Goal):
                        preserved_callbacks.append(cb)
            except Exception:
                pass
            self._subscribe_core_objects(reset=True)
            for cb in preserved_callbacks:
                try:
                    self.event_listener.subscribe(cb)
                except Exception:
                    pass
        # Emit TURN_START only for non-advancement resets; advancement path handles after LEVEL_GENERATED.
        if not advancing:
            try:
                self.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={
                    "level": self.level.name,
                    "turn_index": 1,
                    "advancing": False
                }))
            except Exception:
                pass
        # If we are in the middle of advancement, emit LEVEL_ADVANCE_FINISHED now (TURN_START will be deferred until shop close)
        if advancing:
            try:
                self.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={
                    "level_name": self.level.name,
                    "level_index": self.level_index
                }))
            except Exception:
                pass
            self._advancing_level = False

    def reset_turn(self):
        self._recreate_dice()
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.level_state.consume_turn()
        # Begin next turn lifecycle
        self.begin_turn()

    def roll_dice(self):
        # Wrapper maintained for compatibility; delegate to container
        self.dice_container.roll()

    def calculate_score_from_dice(self):
        return self.dice_container.calculate_selected_score()

    def check_farkle(self):
        return self.dice_container.check_farkle()

    def all_dice_held(self):
        return self.dice_container.all_held()

    def hot_dice_reset(self):
        self._recreate_dice()
        self.set_message("HOT DICE! You can roll all 6 dice again!")

    def mark_scoring_dice(self):
        self.dice_container.mark_scoring()

    def _on_state_change(self, old_state, new_state):
        try:
            self.event_listener.publish(GameEvent(GameEventType.STATE_CHANGED, payload={"old": old_state.name, "new": new_state.name}))
        except Exception:
            pass

    @property
    def dice(self) -> list[Die]:  # backward compatibility accessor
        return self.dice_container.dice

    def any_scoring_selection(self) -> bool:
        return self.dice_container.any_scoring_selection()

    def selection_is_single_combo(self) -> bool:
        return self.dice_container.selection_is_single_combo()

    def update_current_selection_score(self):
        if self.selection_is_single_combo():
            self.current_roll_score, _ = self.calculate_score_from_dice()
        else:
            self.current_roll_score = 0

    # Unified selection preview (migrated from renderer)
    def selection_preview(self) -> tuple[int,int,int,float]:
        if not (self.selection_is_single_combo() and self.any_scoring_selection()):
            return (0,0,0,1.0)
        raw, _ = self.calculate_score_from_dice()
        if raw <= 0:
            return (0,0,0,1.0)
        rk = None
        try:
            rk = self.dice_container.selection_rule_key()
        except Exception:
            rk = None
        if not rk:
            return (raw, raw, raw, 1.0)
        prev = self.compute_preview([(rk, raw)], source="selection")
        return (raw, int(prev.get('selective_effective', raw)), int(prev.get('final_preview', raw)), float(prev.get('multiplier', 1.0)))


    def _auto_lock_selection(self, verb: str = "Auto-locked") -> bool:
        """Lock selected dice if they form exactly one valid scoring combo.

        Adds raw score to pending goal, updates turn score, holds dice, updates message.
        verb: prefix for status message (e.g. 'Auto-locked', 'Locked').
        Returns True on success, False if selection invalid or score zero.
        """
        if not (self.selection_is_single_combo() and self.any_scoring_selection()):
            return False
        add_score, _ = self.calculate_score_from_dice()
        if add_score <= 0:
            return False
        # Identify rule_key for this selection (if available)
        rule_key = None
        try:
            rule_key = self.dice_container.selection_rule_key()
        except Exception:
            rule_key = None
        # Accumulate turn score locally (used for UI enabling) but per-goal pending kept inside Goal
        self.turn_score += add_score
        self.current_roll_score = 0
        # Delegate holding & event emission to container
        self.dice_container.hold_selected_publish()
        gname = self.level.goals[self.active_goal_index][0]
        # Unified preview via compute_preview for lock messaging transparency
        if rule_key:
            try:
                prev = self.compute_preview([(rule_key, add_score)], source="lock_message")
            except Exception:
                prev = None
        else:
            prev = None
        if prev:
            selective = int(prev.get('selective_effective', add_score))
            final_preview = int(prev.get('final_preview', selective))
            mult = float(prev.get('multiplier', 1.0))
            if selective != add_score and final_preview != selective and mult != 1.0:
                self.message = f"{verb} {add_score} -> {selective} -> {final_preview} to {gname}."
            elif selective != add_score:
                self.message = f"{verb} {add_score} -> {selective} to {gname}."
            elif final_preview != add_score and mult != 1.0:
                self.message = f"{verb} {add_score} -> {final_preview} to {gname}."
            else:
                self.message = f"{verb} {add_score} to {gname}."
        else:
            self.message = f"{verb} {add_score} to {gname}."
        self.mark_scoring_dice()
        self.locked_after_last_roll = True
        # Emit LOCK event so the target goal can accumulate pending
        try:
            payload = {
                "goal_index": self.active_goal_index,
                "points": add_score
            }
            if rule_key:
                payload["rule_key"] = rule_key
            self.event_listener.publish(GameEvent(GameEventType.LOCK, payload=payload))
        except Exception:
            pass
        return True

    def handle_lock(self):
        action_handle_lock(self)

    def handle_roll(self):
        action_handle_roll(self)

    def handle_bank(self):
        action_handle_bank(self)

    def handle_next_turn(self):
        action_handle_next_turn(self)

    def create_next_level(self):
        # Emit start of level advancement
        try:
            self.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_STARTED, payload={
                "from_level": self.level.name,
                "from_index": self.level_index
            }))
        except Exception:
            pass
        self.level_index += 1
        prev_level = self.level
        # Generate new level
        self.level = Level.advance(self.level, self.level_index)
        self.level_state = LevelState(self.level)
        self.active_goal_index = 0
        for g in self.level_state.goals:
            g.pending_raw = 0
        # Reset per-level abilities usage
    # Ability manager reset handles reroll availability now.
        if hasattr(self, 'ability_manager'):
            self.ability_manager.reset_level()
        # Event after level data structures generated but before subscriptions/reset
        try:
            self.event_listener.publish(GameEvent(GameEventType.LEVEL_GENERATED, payload={
                "prev_level": prev_level.name,
                "new_level": self.level.name,
                "level_index": self.level_index,
                "goals": [gl.name for gl in self.level_state.goals],
                "max_turns": self.level.max_turns
            }))
        except Exception:
            pass
        # Gold persists; player_gold not reset here.
        # Finish advancement by resetting game state for new level (without losing meta state)
        self._advancing_level = True
        self.reset_game()
        # Defer start of first turn until shop closes; TURN_START will be emitted after SHOP_CLOSED.
        self._defer_turn_start = True

    def draw(self):
        # Base scene
        self.renderer.draw()
        # Overlay misc UI objects (help icon etc.) after base renderer so they appear on top but below modal overlays drawn inside renderer
        for obj in getattr(self, 'ui_misc', []):
            if hasattr(obj, 'draw'):
                try:
                    obj.draw(self.screen)  # type: ignore[attr-defined]
                except Exception:
                    pass
        try:
            import pygame as _pg
            _pg.display.flip()
        except Exception:
            pass


    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    # Allow immediate shop skip via ESC or 'S'
                    if self.relic_manager.shop_open and event.key in (pygame.K_ESCAPE, pygame.K_s):
                        try:
                            self.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP))
                        except Exception:
                            pass
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    # Delegate to UI buttons first
                    for btn in self.ui_buttons:
                        if btn.handle_click(self, (mx, my)):
                            break
                    else:
                        # Misc UI objects (help icon etc.)
                        for obj in self.ui_misc:
                            if hasattr(obj, 'handle_click') and obj.handle_click(self, (mx,my)):  # type: ignore[attr-defined]
                                break
                        else:
                            # Fallback to renderer click logic (dice, goals, shop, etc.)
                            self.renderer.handle_click(self, (mx, my))
            # Use unified draw so modal overlays (shop, rules, relic panel, player HUD) render.
            # Previously this called renderer.draw() directly which skipped ShopOverlay and others.
            self.draw()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()

    def set_message(self, text: str):
        """Set current UI status message.

        Future extension: maintain a history or timestamp for debugging/logs.
        """
        self.message = text


    # --- ability logic -------------------------------------------------
    # Reroll functionality has been moved entirely into the ability system.

    # Internal: subscribe core objects
    def _subscribe_core_objects(self, reset: bool = False):
        if reset:
            self.event_listener = EventListener()
        # Subscribe each object's on_event method
        # (Re)subscribe input controller first so it can mediate requests before goals react if needed.
        if hasattr(self, 'input_controller') and self.input_controller:
            self.event_listener.subscribe(self.input_controller.on_event)
        self.event_listener.subscribe(self.player.on_event)
        for g in self.level_state.goals:
            g.game = self  # type: ignore[attr-defined]
            self.event_listener.subscribe(g.on_event)
        # Ensure game progression listener is present after resets
        self.event_listener.subscribe(self.on_event)

    # Auto progression logic
    def on_event(self, event: GameEvent):  # type: ignore[override]
        et = event.type
        # Detect all mandatory fulfilled immediately on GOAL_FULFILLED
        if et == GameEventType.GOAL_FULFILLED:
            if self.level_state._all_mandatory_fulfilled() and not self.level_state.completed:
                self.level_state.completed = True
                # After completion we wait for TURN_END if not already ended; if turn already ended (banked) we advance immediately.
                if any(e.type == GameEventType.TURN_END for e in getattr(self, '_recent_events', [])):
                    self._advance_level_post_turn()
        elif et == GameEventType.BANK:
            # Initialize tracking of outstanding score applications for this bank.
            # Count goals with pending_raw > 0 at bank time.
            pending_goals = sum(1 for g in self.level_state.goals if getattr(g, 'pending_raw', 0) > 0 and not g.is_fulfilled())
            self._bank_applications_expected = pending_goals
            self._bank_applications_seen = 0
            # Edge case: no pending goals -> emit TURN_END immediately (bank of zero pending shouldn't happen due to guard but be safe)
            if pending_goals == 0:
                try:
                    self.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason": "banked"}))
                except Exception:
                    pass
        elif et == GameEventType.SCORE_APPLIED:
            # Increment seen count; when all expected have applied, emit TURN_END.
            if hasattr(self, '_bank_applications_expected'):
                self._bank_applications_seen += 1
                if self._bank_applications_seen >= getattr(self, '_bank_applications_expected', 0):
                    try:
                        self.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason": "banked"}))
                    except Exception:
                        pass
                    # Cleanup tracking vars
                    self._bank_applications_expected = 0
                    self._bank_applications_seen = 0
        elif et == GameEventType.TURN_END:
            reason = event.get("reason")
            # If the level just completed this turn, advance now
            if self.level_state.completed and reason in ("banked", "farkle", "level_complete"):
                self._advance_level_post_turn()
            if reason == "banked":
                # Now that scoring application cycle finished, clear per-turn tallies
                self.turn_score = 0
                self.current_roll_score = 0
            # Failure detection: out of turns and not complete
            if not self.level_state.completed and self.level_state.turns_left == 0 and not self.level_state._all_mandatory_fulfilled():
                if not self.level_state.failed:
                    self.level_state.failed = True
                    unfinished = [self.level.goals[i][0] for i in self.level_state.mandatory_indices if not self.level_state.goals[i].is_fulfilled()]
                    try:
                        self.event_listener.publish(GameEvent(GameEventType.LEVEL_FAILED, payload={
                            "level_name": self.level.name,
                            "level_index": self.level_index,
                            "unfinished": unfinished
                        }))
                    except Exception:
                        pass
                    # Restart same level
                    self.reset_game()
        # Track a small rolling window of recent events for ordering decisions
        if not hasattr(self, '_recent_events'):
            self._recent_events: list[GameEvent] = []
        self._recent_events.append(event)
        if len(self._recent_events) > 50:
            self._recent_events.pop(0)
        # Shop lifecycle transitions
        if et == GameEventType.LEVEL_ADVANCE_FINISHED:
            # Enter shop state
            try:
                self.state_manager.transition_to_shop()
            except Exception:
                pass
        elif et == GameEventType.SHOP_CLOSED:
            # Leave shop and emit TURN_START for new level start if not already rolled
            try:
                self.state_manager.exit_shop_to_pre_roll()
                # Clear defer flag and begin first turn now
                self._defer_turn_start = False
                self.begin_turn(from_shop=True)
            except Exception:
                pass

    def _advance_level_post_turn(self):
        # Emit LEVEL_COMPLETE if not already
        already = any(e.type == GameEventType.LEVEL_COMPLETE for e in getattr(self, '_recent_events', []))
        if not already:
            try:
                self.event_listener.publish(GameEvent(GameEventType.LEVEL_COMPLETE, payload={
                    "level_name": self.level.name,
                    "level_index": self.level_index
                }))
            except Exception:
                pass
        # Begin advancement
        self.create_next_level()
    
    # --- Turn initialization -------------------------------------------------
    def begin_turn(self, initial: bool = False, advancing: bool = False, fallback: bool = False, from_shop: bool = False):
        """Centralize start-of-turn state initialization and TURN_START emission.

        Parameters:
            initial: first ever game turn.
            advancing: beginning of a new level after advancement.
            fallback: defensive re-emission case.
            from_shop: resuming after shop close.
        """
        try:
            # If not in shop, ensure PRE_ROLL state
            if self.state_manager.get_state() != self.state_manager.state.PRE_ROLL:
                # Only set if not SHOP (shop must explicitly close first)
                if self.state_manager.get_state() != self.state_manager.state.SHOP:
                    self.state_manager.set_state(self.state_manager.state.PRE_ROLL)
            # Reset per-turn selection flags
            self.active_goal_index = 0
            self.locked_after_last_roll = False
            # Ensure dice selection flags cleared (values preserved until first roll unless reset_turn already did)
            for d in self.dice:
                d.selected = False
                d.scoring_eligible = False
            self.mark_scoring_dice()
            payload = {
                "level": self.level.name,
                "turn_index": 1 if (initial or advancing) else None,
                "turns_left": self.level_state.turns_left,
                "advancing": advancing,
                "fallback": fallback,
                "from_shop": from_shop
            }
            # Remove None entries
            payload = {k:v for k,v in payload.items() if v is not None and v is not False}
            self.event_listener.publish(GameEvent(GameEventType.TURN_START, payload=payload))
        except Exception:
            pass
