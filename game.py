import pygame, sys
from game_state_manager import GameStateManager
from scoring import ScoringRules, SingleValue, ThreeOfAKind, Straight6
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
from relic_manager import RelicManager

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
        # Event listener hub
        self.event_listener = EventListener()
        # Subscribe player & goals
        self._subscribe_core_objects()
        # Subscribe relic manager
        self.event_listener.subscribe(self.relic_manager.on_event)
        # Input controller (handles REQUEST_* events)
        self.input_controller = InputController(self)
        self.event_listener.subscribe(self.input_controller.on_event)
        # Emit initial TURN_START for the very first turn
        try:
            self.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={"level": self.level.name, "turn_index": 1}))
        except Exception:
            pass
        # Subscribe game itself for auto progression
        self.event_listener.subscribe(self.on_event)
    # dice already initialized by container

    def _init_rules(self):
        self.rules.add_rule(ThreeOfAKind(1, 1000))
        self.rules.add_rule(ThreeOfAKind(2, 200))
        self.rules.add_rule(ThreeOfAKind(3, 300))
        self.rules.add_rule(ThreeOfAKind(4, 400))
        self.rules.add_rule(ThreeOfAKind(5, 500))
        self.rules.add_rule(ThreeOfAKind(6, 600))
        self.rules.add_rule(SingleValue(1, 100))
        self.rules.add_rule(SingleValue(5, 50))
        self.rules.add_rule(Straight6(1500))

    def reset_dice(self):
        self.dice_container.reset_all()

    def reset_game(self):
        # When called after win/lose we keep current level (already advanced on win)
        self.reset_dice()
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.state_manager = GameStateManager(on_change=self._on_state_change)
        self.level_state.reset()
        self.active_goal_index = 0
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
        # If we are in the middle of advancement, now emit LEVEL_ADVANCE_FINISHED (after new TURN_START)
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
        self.dice_container.reset_all()
        self.turn_score = 0
        self.current_roll_score = 0
        self.message = "Click ROLL to start!"
        self.mark_scoring_dice()
        self.level_state.consume_turn()
        self.state_manager.transition_to_start()
        self.active_goal_index = 0
        # Clear per-goal pending
        for g in self.level_state.goals:
            g.pending_raw = 0
        self.locked_after_last_roll = False
        try:
            remaining_turns = self.level_state.turns_left
            self.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={"level": self.level.name, "turns_left": remaining_turns}))
        except Exception:
            pass

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
        self.dice_container.reset_all()
        self.set_message("HOT DICE! You can roll all 6 dice again!")
        self.mark_scoring_dice()
        # Reset lock requirement after hot dice
        self.locked_after_last_roll = False

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
        # Accumulate turn score locally (used for UI enabling) but per-goal pending kept inside Goal
        self.turn_score += add_score
        self.current_roll_score = 0
        # Delegate holding & event emission to container
        self.dice_container.hold_selected_publish()
        gname = self.level.goals[self.active_goal_index][0]
        self.message = f"{verb} {add_score} to {gname}."
        self.mark_scoring_dice()
        self.locked_after_last_roll = True
        # Emit LOCK event so the target goal can accumulate pending
        try:
            self.event_listener.publish(GameEvent(GameEventType.LOCK, payload={
                "goal_index": self.active_goal_index,
                "points": add_score
            }))
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
        # Emit TURN_START for new level now (guaranteed after LEVEL_GENERATED)
        try:
            self.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={
                "level": self.level.name,
                "turn_index": 1,
                "advancing": True
            }))
        except Exception:
            pass
        # Fallback (should be redundant now) retained for safety
        try:
            recent_types = [e.type for e in getattr(self, '_recent_events', [])[-20:]]
            gen_positions = [i for i,t in enumerate(recent_types) if t == GameEventType.LEVEL_GENERATED]
            if gen_positions:
                last_gen = gen_positions[-1]
                if GameEventType.TURN_START not in recent_types[last_gen+1:]:
                    self.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={
                        "level": self.level.name,
                        "turn_index": 1,
                        "fallback": True
                    }))
        except Exception:
            pass

    def draw(self):
        self.renderer.draw()


    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    self.renderer.handle_click((mx, my))
                    if ROLL_BTN.collidepoint(mx, my):
                        self.event_listener.publish(GameEvent(GameEventType.REQUEST_ROLL))
                    if LOCK_BTN.collidepoint(mx, my):
                        self.event_listener.publish(GameEvent(GameEventType.REQUEST_LOCK))
                    if BANK_BTN.collidepoint(mx, my):
                        self.event_listener.publish(GameEvent(GameEventType.REQUEST_BANK))
                    if NEXT_BTN.collidepoint(mx, my):
                        self.event_listener.publish(GameEvent(GameEventType.REQUEST_NEXT_TURN))
            self.renderer.draw()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()

    def set_message(self, text: str):
        """Set current UI status message.

        Future extension: maintain a history or timestamp for debugging/logs.
        """
        self.message = text

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
                self.state_manager.exit_shop_to_start()
                # Emit a fresh TURN_START so UI resumes; include turns_left
                self.event_listener.publish(GameEvent(GameEventType.TURN_START, payload={
                    "level": self.level.name,
                    "turn_index": 1,
                    "from_shop": True,
                    "turns_left": self.level_state.turns_left
                }))
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
