import pygame
# Explicit sprite module imports to ensure classes load (avoid silent try/except swallowing)
try:
    import farkle.ui.sprites.die_sprite as die_sprite  # ensures DieSprite definition loaded
    import farkle.ui.sprites.ui_sprites as ui_sprites  # UIButtonSprite
    import farkle.ui.sprites.overlay_sprites as overlay_sprites  # HelpIconSprite, RulesOverlaySprite
    import farkle.ui.sprites.goal_sprites as goal_sprites  # GoalSprite
    import farkle.ui.sprites.relic_panel_sprite as relic_panel_sprite # RelicPanelSprite
    import farkle.ui.sprites.hud_sprites as hud_sprites  # PlayerHUDSprite, GodsPanelSprite
    # Sprite modules imported successfully.
except Exception as _e:
    # Log silently in production; could hook into a logger.
    pass
from farkle.core.game_state_manager import GameStateManager
from farkle.scoring.scoring import (
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
from farkle.dice.die import Die
from farkle.dice.dice_container import DiceContainer
from farkle.level.level import Level, LevelState
from farkle.players.player import Player
from farkle.core.game_event import GameEvent, GameEventType
from farkle.core.event_listener import EventListener
from farkle.core.actions import handle_lock as action_handle_lock, handle_roll as action_handle_roll, handle_bank as action_handle_bank, handle_next_turn as action_handle_next_turn
from farkle.ui.input_controller import InputController
from farkle.ui.renderer import GameRenderer
from farkle.ui.ui_objects import build_core_buttons, HelpIcon, RelicPanel, RulesOverlay
from farkle.core.game_object import GameObject
from farkle.relics.relic_manager import RelicManager
from farkle.abilities.ability_manager import AbilityManager
from farkle.scoring.scoring_manager import ScoringManager
from farkle.gods.gods_manager import GodsManager, God
from farkle.meta.statistics_tracker import StatisticsTracker
from farkle.ui.choice_window_manager import ChoiceWindowManager

class Game:
    def __init__(self, screen, font, clock, level: Level | None = None, *, rng_seed: int | None = None, auto_initialize: bool = True, skip_god_selection: bool = False):
        """Core gameplay model: state, dice, scoring, events.

        UI concerns (tooltips, hotkeys, modal shop rendering) are handled by screen
        classes (`GameScreen`, `ShopScreen`). This class intentionally avoids direct
        per-frame input side-effects beyond event publication so it remains testable
        with synthetic events.
        
        Args:
            screen: Pygame display surface
            font: Main font for rendering
            clock: Pygame clock for timing
            level: Optional initial level (defaults to single-goal prototype)
            rng_seed: Optional seed for deterministic testing
            auto_initialize: If True, calls initialize() immediately. Set False to defer initialization.
        """
        # Store construction parameters
        self.screen = screen
        self.font = font
        self.clock = clock
        self._initial_level = level
        self._rng_seed = rng_seed
        self._skip_god_selection = skip_god_selection
        
        # Small font for auxiliary text
        try:
            self.small_font = pygame.font.Font(None, 22)
        except Exception:
            self.small_font = font
        
        # Initialize basic attributes that other code may check before initialize()
        self.rng = None
        self.level = None
        self.level_state = None
        self.event_listener = None
        self.state_manager = None
        
        # Auto-initialize if requested (default for backward compatibility)
        if auto_initialize:
            self.initialize()
    
    def initialize(self):
        """Initialize all game systems after construction.
        
        This method can be called after creating the Game object to set up
        all the complex subsystems. Separating this from __init__ allows
        external code to create the Game object first, then initialize it
        when ready.
        """
        # Global randomness source (seeded optionally for deterministic tests)
        # Initialize RNG before level creation so we can pass it
        try:
            from farkle.core.random_source import RandomSource
            self.rng = RandomSource(seed=self._rng_seed)
        except Exception:
            self.rng = None  # fallback; direct random usage will occur until fixed
        
        # Use provided level or create a default level with disaster from JSON
        self.level = self._initial_level or Level.single(
            name="",  # Name will be replaced by disaster title from JSON
            target_goal=300, 
            max_turns=3,
            description="",
            rng=self.rng
        )
        self.level_state = LevelState(self.level, self)
        self.active_goal_index: int = 0
        self.rules = ScoringRules()
        self._init_rules()
        self.state_manager = GameStateManager(on_change=self._on_state_change)
        # Centralized scoring manager (replaces inline preview logic)
        self.scoring_manager = ScoringManager(self)
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
        self.player = Player(self)
        # Relic manager handles between-level shop & relic aggregation
        self.relic_manager = RelicManager(self)
        # Gods manager: manages worshipped gods and applies selective effects
        self.gods = GodsManager(self)
        # Choice window manager: handles all selection screens (god selection, shop, etc.)
        self.choice_window_manager = ChoiceWindowManager(self)
        # Renderer handles all drawing/UI composition
        self.renderer = GameRenderer(self)
        # Recreate dice now that renderer exists so DieSprites attach to layered groups (initial container may have created dice before renderer ready)
        try:
            self.dice_container.reset_all()
            self.ui_dynamic = list(self.dice_container.dice)
        except Exception:
            pass
        # UI game objects (buttons) built after renderer/font ready
        self.ui_buttons = build_core_buttons(self)
        # Sprite wrappers for buttons (layered UI). Keep logical buttons for event logic & tests.
        # Attach game reference so sprite gating logic can access state.
        for _btn in self.ui_buttons:
            try:
                setattr(_btn, 'game', self)
            except Exception:
                pass
        try:
            from farkle.ui.sprites.ui_sprites import UIButtonSprite
            for btn in self.ui_buttons:
                try:
                    UIButtonSprite(btn, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
                except Exception:
                    pass
        except Exception:
            pass
        # Misc UI objects (help icon, overlays later)
        self.show_help = False
    # Shop interaction handled via separate ShopScreen/overlay sprite; legacy inline overlay fully removed.
        self.ui_misc: list[GameObject] = [
            HelpIcon(10, self.screen.get_height() - 50, self, 40),
            RelicPanel(self),
            RulesOverlay(self),
            self.player,
            self.gods,
        ]
        # Wrap certain misc UI objects with sprites (help icon, rules overlay)
        try:
            from farkle.ui.sprites.overlay_sprites import HelpIconSprite, RulesOverlaySprite
            for o in list(self.ui_misc):
                try:
                    if o.__class__.__name__ == 'HelpIcon':
                        HelpIconSprite(o, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
                        setattr(o, 'has_sprite', True)
                    elif o.__class__.__name__ == 'RulesOverlay':
                        RulesOverlaySprite(o, self, self.renderer.sprite_groups['overlay'], self.renderer.layered)
                        setattr(o, 'has_sprite', True)
                except Exception:
                    pass
        except Exception:
            pass
        # Choice window sprite (modal) for god selection, shop, etc.
        self.choice_window_sprite = None
        
        # Debug flag for layer printing
        self._debug_layers_printed = False
        
        try:
            from farkle.ui.sprites.choice_window_sprite import ChoiceWindowSprite
            # Create sprite that will show/hide based on choice_window_manager state
            def _safe_create_choice_window_sprite():
                try:
                    # The sprite checks if game has choice_window_manager and if there's an active window
                    # We'll create a dummy window object that the sprite uses for its visible_predicate
                    dummy_window = type('obj', (object,), {'is_open': lambda self: False})()
                    self.choice_window_sprite = ChoiceWindowSprite(dummy_window, self, self.renderer.sprite_groups['modal'], self.renderer.layered)
                except Exception as e:
                    self.choice_window_sprite = None
                    setattr(self, 'last_choice_window_sprite_error', repr(e))
                    print(f"ERROR: Failed to create ChoiceWindowSprite: {e}")
                    import traceback
                    traceback.print_exc()
            _safe_create_choice_window_sprite()
        except Exception as e:
            print(f"ERROR: Exception in choice window sprite setup: {e}")
            import traceback
            traceback.print_exc()
        # Goal & relic panel sprites
        self._init_goal_and_panel_sprites()
        # Player & Gods HUD sprites
        try:
            from farkle.ui.sprites.hud_sprites import PlayerHUDSprite, GodsPanelSprite
            PlayerHUDSprite(self.player, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
            setattr(self.player, 'has_sprite', True)
            GodsPanelSprite(self.gods, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
            setattr(self.gods, 'has_sprite', True)
        except Exception:
            pass
        # Removed transient GameStateDebugSprite used for debugging state visibility.
        # Event listener hub (create before abilities so filtered subscriptions can attach)
        self.event_listener = EventListener()
        # Statistics tracker for meta progression (achievements, upgrades, etc.)
        self.statistics_tracker = StatisticsTracker(self)
        # Ability manager owns reroll ability; create then subscribe filtered
        self.ability_manager = AbilityManager(self)
        try:
            self.ability_manager.activate_all()
        except Exception:
            pass
        # Internal flag: when True we defer TURN_START emission (e.g., awaiting shop interaction after advancement)
        self._defer_turn_start = False
        # Subscribe player & goals
        self._subscribe_core_objects()
        # Subscribe relic manager
        self.event_listener.subscribe(self.relic_manager.on_event)
        # Subscribe scoring manager for incremental modifier events
        self.event_listener.subscribe(self.scoring_manager.on_event)
        # Input controller (handles REQUEST_* events)
        self.input_controller = InputController(self)
        self.event_listener.subscribe(self.input_controller.on_event)
        # Gods will be selected by player at game start (no default gods)
        # Emit LEVEL_GENERATED for the initial level (so temple income is awarded on first level)
        try:
            self.event_listener.publish(GameEvent(GameEventType.LEVEL_GENERATED, payload={
                "prev_level": None,
                "new_level": self.level.name,
                "level_index": self.level_index,
                "goals": [gl.name for gl in self.level_state.goals],
                "max_turns": self.level.max_turns
            }))
        except Exception:
            pass
        # Open god selection window at game start (instead of auto-starting turn)
        if self._skip_god_selection:
            # For tests: skip god selection and go straight to first turn
            try:
                self.begin_turn(initial=True)
            except Exception:
                pass
        else:
            # Normal flow: open god selection window
            try:
                self._open_god_selection_window()
            except Exception as e:
                # Log the error for debugging
                import traceback
                print(f"ERROR: Failed to open god selection window: {e}")
                traceback.print_exc()
                # Fallback: if god selection fails, start turn normally
                try:
                    self.begin_turn(initial=True)
                except Exception:
                    pass
        # Subscribe game itself for auto progression
        self.event_listener.subscribe(self.on_event)
    # dice already initialized by container

    def _init_goal_and_panel_sprites(self):
        """Instantiate GoalSprite and RelicPanelSprite for current goals & relic panel.

        Safe to call multiple times: existing sprites persist; new goals (after level advance)
        get wrapped. Relic panel sprite re-created idempotently.
        """
        try:
            from farkle.ui.sprites.goal_sprites import GoalSprite
            from farkle.ui.sprites.relic_panel_sprite import RelicPanelSprite
            # Wrap goals
            for gl in self.level_state.goals:
                if not getattr(gl, 'has_sprite', False):
                    try:
                        GoalSprite(gl, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
                    except Exception:
                        pass
            # Find relic panel
            from farkle.ui.ui_objects import RelicPanel as _RelicPanel
            panel = next((o for o in self.ui_misc if isinstance(o, _RelicPanel)), None)
            if panel and not getattr(panel, 'has_sprite', False):  # retain conditional until panel always guaranteed sprite earlier
                try:
                    RelicPanelSprite(panel, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
                except Exception:
                    pass
        except Exception:
            pass

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

    def compute_preview(self, parts: list[tuple[str,int]], source: str = "selection") -> dict:
        """Delegated preview to `ScoringManager` (legacy compatibility wrapper).

        Prefer calling `self.scoring_manager.preview` directly; this helper remains
        for transitional code. If scoring_manager missing, returns trivial structure.
        """
        sm = getattr(self, 'scoring_manager', None)
        if sm:
            return sm.preview(parts, source=source)
        total = sum(p[1] for p in parts)
        return {
            "parts": [{"rule_key": rk, "raw": raw, "adjusted": raw} for rk, raw in parts],
            "total_raw": total,
            "adjusted_total": total,
        }

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
                from farkle.goals.goal import Goal as _Goal
                # Unsubscribe existing goal callbacks
                for cb in list(getattr(self.event_listener, "_subs_all", [])):
                    bound_self = getattr(cb, "__self__", None)
                    if bound_self is not None and isinstance(bound_self, _Goal):
                        try:
                            self.event_listener.unsubscribe(cb)
                        except Exception:
                            pass
                # Subscribe new level goals
                for gobj in self.level_state.goals:
                    self.event_listener.subscribe(gobj.on_event)
                # Ensure game.on_event remains subscribed
                if self.on_event not in getattr(self.event_listener, "_subs_all", []):
                    self.event_listener.subscribe(self.on_event)
            except Exception:
                pass
        else:
            # Non-advancement path: full reset including listener replacement (retain external subscribers)
            preserved_callbacks: list = []
            try:
                from farkle.goals.goal import Goal as _Goal
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
        return self.rules.selection_is_single_combo(self.dice_container.selection_values())

    def update_current_selection_score(self):
        if self.selection_is_single_combo():
            self.current_roll_score, _ = self.calculate_score_from_dice()
        else:
            self.current_roll_score = 0

    # Unified selection preview (migrated from renderer)
    def selection_preview(self, goal=None) -> tuple[int,int,int,float]:
        if not (self.selection_is_single_combo() and self.any_scoring_selection()):
            return (0,0,0,1.0)
        raw, _ = self.calculate_score_from_dice()
        if raw <= 0:
            return (0,0,0,1.0)
        rule_key = None
        try:
            rule_key = self.rules.selection_rule_key(self.dice_container.selection_values())
        except Exception:
            rule_key = None
        if not rule_key:
            return (raw, raw, raw, 1.0)
        # Delegate modifier application & preview assembly to ScoringManager so selective bonuses apply.
        try:
            scoring_mgr = getattr(self, 'scoring_manager', None)
            if scoring_mgr:
                # Fetch active goal if available for conditional modifiers
                if goal is None:
                    try:
                        goal = self.level_state.goals[self.active_goal_index]
                    except Exception:
                        goal = None
                preview = scoring_mgr.preview([(rule_key, raw)], source="selection", goal=goal)
                adj = int(preview.get('adjusted_total', raw))
                return (raw, adj, adj, 1.0)
        except Exception:
            pass
        return (raw, raw, raw, 1.0)


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
            rule_key = self.rules.selection_rule_key(self.dice_container.selection_values())
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
            adjusted = int(prev.get('adjusted_total', add_score))
            if adjusted != add_score:
                self.message = f"{verb} {add_score} -> {adjusted} to {gname}."
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
        # Generate new level with progressive petitions
        self.level = Level.advance(self.level, self.level_index, rng=self.rng)
        self.level_state = LevelState(self.level, self)
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
        # Ensure new level goals get sprites
        try:
            self._init_goal_and_panel_sprites()
        except Exception:
            pass

    def draw(self):
        # Base scene
        self.renderer.draw()
        # Overlay misc UI objects (help icon etc.) after base renderer so they appear on top but below modal overlays drawn inside renderer
        for obj in getattr(self, 'ui_misc', []):
            # Skip if object now represented by a sprite
            if getattr(obj, 'has_sprite', False):
                continue
            if hasattr(obj, 'draw'):
                try:
                    obj.draw(self.screen)  # type: ignore[attr-defined]
                except Exception:
                    pass
        # NOTE: Removed internal display.flip() to avoid double flipping; App.run() handles flipping once per frame.



    # --- Single-step helpers for App controller (screen system) ---
    def _process_event_single(self, event):
        """Process one pygame event (subset of run loop logic) so an external App can drive per-frame iteration."""
        import pygame as _pg
        if event.type == pygame.MOUSEMOTION:
            # Tooltip logic handled in GameScreen; ignore.
            pass
        elif event.type == pygame.KEYDOWN:
            return  # Key handling now performed in GameScreen.
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            
            # Check choice window first - if open, it should consume all clicks
            if self.choice_window_sprite and self.choice_window_sprite.choice_window:
                if self.choice_window_sprite.choice_window.is_open():
                    if hasattr(self.choice_window_sprite, 'handle_click'):
                        if self.choice_window_sprite.handle_click(self, (mx, my)):
                            return
                    # Even if handle_click doesn't exist or returns False, consume the click
                    # to prevent it from going to underlying UI
                    return
            
            if getattr(event, 'button', None) == 3:
                if self.state_manager.get_state() in (self.state_manager.state.ROLLING, self.state_manager.state.FARKLE, self.state_manager.state.SELECTING_TARGETS):
                    if self.state_manager.get_state() == self.state_manager.state.SELECTING_TARGETS:
                        # Check if ability targets goals
                        abm = getattr(self, 'ability_manager', None)
                        selecting_ability = abm.selecting_ability() if abm else None
                        if selecting_ability:
                            if selecting_ability.target_type == 'goal':
                                # Check if right-click is on a goal to finalize
                                goal_hit = False
                                for idx, goal in enumerate(self.level_state.goals):
                                    rect = getattr(goal, '_last_rect', None)
                                    if rect and rect.collidepoint(mx, my):
                                        goal_hit = True
                                        # If goal not already selected, select it first
                                        if idx not in getattr(selecting_ability, 'collected_targets', []):
                                            abm.attempt_target('goal', idx)
                                        # Finalize selection
                                        if abm.finalize_selection():
                                            return
                                        break
                                # If not clicking on goal, cancel selection
                                if not goal_hit and self.cancel_target_selection(reason="cancelled"):
                                    return
                                return
                            elif selecting_ability.target_type == 'die':
                                # Original die handling
                                die_hit = any((not d.held) and d.rect().collidepoint(mx,my) for d in self.dice)
                                if not die_hit and self.cancel_target_selection(reason="cancelled"):
                                    return
                    else:
                        die_hit = any((not d.held) and d.rect().collidepoint(mx,my) for d in self.dice)
                        if not die_hit and self.clear_all_selected_dice():
                            self.set_message("Selection cleared."); return
                    self._handle_die_click(mx,my, button=3)
                    return
            for btn in self.ui_buttons:
                if btn.handle_click(self, (mx,my)):
                    return
            for obj in self.ui_misc:
                if hasattr(obj, 'handle_click') and obj.handle_click(self, (mx,my)):
                    return
            # Overlay sprites (shop, rules, farkle banner). Shop overlay should intercept first.
            try:
                overlay_group = self.renderer.sprite_groups.get('overlay')
                if overlay_group:
                    # Ensure deterministic ordering: shop overlay first if present
                    sprites = list(overlay_group)
                    sprites.sort(key=lambda s: 0 if s.__class__.__name__ == 'ShopOverlaySprite' else 1)
                    for spr in sprites:
                        if hasattr(spr, 'handle_click') and spr.handle_click(self, (mx,my)):
                            return
            except Exception:
                pass
            self.renderer.handle_click(self, (mx,my))

    def _step_frame(self):
        """Execute draw + tooltip resolution + tick once (subset of original run loop)."""
        self.draw()

    def set_message(self, text: str):
        """Set current UI status message.

        Future extension: maintain a history or timestamp for debugging/logs.
        """
        self.message = text

    # Unified die click handling (left/right)
    def _handle_die_click(self, mx: int, my: int, button: int = 1) -> bool:
        """Handle a click on dice area.

        button 1: normal select toggle (now unified here)
        button 3: select scoring die and auto-lock if valid combo.
        Returns True if consumed.
        """
        play_states = (self.state_manager.state.ROLLING, self.state_manager.state.FARKLE, self.state_manager.state.SELECTING_TARGETS)
        # Find die under cursor
        target = None
        for d in self.dice:
            if (not d.held) and d.rect().collidepoint(mx, my):
                if hasattr(d, 'should_interact') and not d.should_interact(self):
                    continue
                target = d; break
        if target is None:
            return False
        if self.state_manager.get_state() not in play_states:
            return False
        # Ability targeting precedence
        abm = getattr(self, 'ability_manager', None)
        if self.state_manager.get_state() == self.state_manager.state.SELECTING_TARGETS and abm and abm.selecting_ability():
            sel = abm.selecting_ability()
            if sel and sel.target_type == 'die':
                die_index = self.dice.index(target)
                if button == 1:  # left click toggle
                    if abm.attempt_target('die', die_index):
                        return True
                elif button == 3:  # right click finalize
                    # Ensure current die is selected before finalizing (toggle if not)
                    if die_index not in getattr(sel, 'collected_targets', []):
                        abm.attempt_target('die', die_index)
                    if abm.finalize_selection():
                        return True
        if button == 3:
            if target.scoring_eligible:
                # Right-click should only act if the resulting selection can lock immediately.
                # If die not selected, test whether selecting it would yield a single combo.
                if not target.selected:
                    # Temporarily select
                    target.toggle_select()
                    self.update_current_selection_score()
                    lockable = self.selection_is_single_combo() and self.any_scoring_selection()
                    if not lockable:
                        # Revert and do nothing
                        target.toggle_select()
                        self.update_current_selection_score()
                        return True  # consumed but no change
                    # Emit DIE_SELECTED only if we proceed to lock
                    try:
                        self.event_listener.publish(GameEvent(GameEventType.DIE_SELECTED, payload={"index": self.dice.index(target)}))
                    except Exception:
                        pass
                else:
                    # Already selected: only proceed if selection currently lockable
                    if not (self.selection_is_single_combo() and self.any_scoring_selection()):
                        return True  # do nothing
                # Perform lock
                if self.state_manager.get_state() == self.state_manager.state.PRE_ROLL:
                    try:
                        self.state_manager.transition_to_rolling()
                    except Exception:
                        pass
                if self._auto_lock_selection("Locked"):
                    self.set_message(self.message + " (right-click)")
                    try:
                        self.event_listener.publish(GameEvent(GameEventType.TURN_LOCK_ADDED, payload={"turn_score": self.turn_score}))
                    except Exception:
                        pass
                return True
            return False
        if button == 1:
            # Standard selection toggle provided target is scoring eligible and not in targeting mode (handled above)
            if target.scoring_eligible:
                was_selected = target.selected
                target.toggle_select()
                self.update_current_selection_score()
                # Emit appropriate event
                try:
                    self.event_listener.publish(GameEvent(GameEventType.DIE_SELECTED if not was_selected else GameEventType.DIE_DESELECTED, payload={"index": self.dice.index(target)}))
                except Exception:
                    pass
                return True
            return False
        return False

    # Centralized cancellation utility for ability target selection
    def cancel_target_selection(self, reason: str = "cancelled") -> bool:
        if self.state_manager.get_state() != self.state_manager.state.SELECTING_TARGETS:
            return False
        abm = getattr(self, 'ability_manager', None)
        if not abm:
            return False
        sel = abm.selecting_ability()
        if not sel:
            return False
        sel.selecting = False
        try:
            self.state_manager.exit_selecting_targets()
        except Exception:
            pass
        try:
            self.event_listener.publish(GameEvent(GameEventType.TARGET_SELECTION_FINISHED, payload={"ability": sel.id, "reason": reason}))
        except Exception:
            pass
        try:
            self.set_message(f"{sel.name} selection cancelled.")
        except Exception:
            pass
        return True

    def clear_all_selected_dice(self) -> bool:
        """Deselect every currently selected, scoring-eligible die. Returns True if any were deselected."""
        any_deselected = False
        for d in self.dice:
            if d.selected:
                d.selected = False
                any_deselected = True
                try:
                    self.event_listener.publish(GameEvent(GameEventType.DIE_DESELECTED, payload={"index": self.dice.index(d)}))
                except Exception:
                    pass
        if any_deselected:
            self.update_current_selection_score()
        return any_deselected

    def _open_god_selection_window(self):
        """Open a choice window for selecting patron gods at game start."""
        from farkle.ui.choice_window import ChoiceWindow, ChoiceItem
        from farkle.gods.demeter import Demeter
        from farkle.gods.ares import Ares
        from farkle.gods.hades import Hades
        from farkle.gods.hermes import Hermes
        
        def select_god(game, god_class):
            """Called when a god is selected - create and worship the god."""
            god = god_class(game=game)
            # Add to worshipped gods
            current_gods = list(game.gods.worshipped)
            current_gods.append(god)
            game.gods.set_worshipped(current_gods)
        
        # Create choice items for each god
        all_items = [
            ChoiceItem(
                id="demeter",
                name="Demeter",
                description="Goddess of harvest, growth, and natural abundance",
                payload=Demeter,
                on_select=select_god,
                effect_text="Level up through nature goals. Gain +20% to nature scoring at level 1, Sanctify ability at level 2, and double nature rewards at level 3."
            ),
            ChoiceItem(
                id="ares",
                name="Ares",
                description="God of war, conflict, and martial prowess",
                payload=Ares,
                on_select=select_god,
                effect_text="Level up through warfare goals. Gain +20% to warfare scoring at level 1, Sanctify ability at level 2, and double warfare rewards at level 3."
            ),
            ChoiceItem(
                id="hades",
                name="Hades",
                description="God of the underworld and the dead",
                payload=Hades,
                on_select=select_god,
                effect_text="Level up through spirit goals. Gain +20% to spirit scoring at level 1, Sanctify ability at level 2, and double spirit rewards at level 3."
            ),
            ChoiceItem(
                id="hermes",
                name="Hermes",
                description="God of commerce, travel, and cunning",
                payload=Hermes,
                on_select=select_god,
                effect_text="Level up through commerce goals. Gain +20% to commerce scoring at level 1, Sanctify ability at level 2, and double commerce rewards at level 3."
            )
        ]
        
        # Randomly select 3 gods to offer
        import random
        items = random.sample(all_items, 3)
        
        # Create choice window
        window = ChoiceWindow(
            title="Choose Your Patron God",
            items=items,
            window_type="god_selection",
            allow_skip=False,  # Must select a god
            allow_minimize=True,  # Can minimize to see game state
            min_selections=1,
            max_selections=1  # Only one god - auto-confirms on selection
        )
        
        # Set game state to CHOICE_WINDOW to disable normal UI interactions
        from farkle.core.game_state_enum import GameState
        self.state_manager.set_state(GameState.CHOICE_WINDOW)
        
        # Open the window
        self.choice_window_manager.open_window(window)
        
        # Update the choice window sprite to show the new window
        if self.choice_window_sprite:
            try:
                self.choice_window_sprite.choice_window = window
                self.choice_window_sprite.sync_from_logical()
            except Exception as e:
                print(f"ERROR: Failed to update choice window sprite: {e}")
                import traceback
                traceback.print_exc()


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
            self.event_listener.subscribe(g.on_event)
        # Subscribe gods manager if present
        if hasattr(self, 'gods') and self.gods:
            self.event_listener.subscribe(self.gods.on_event)
        # Ensure game progression listener is present after resets
        self.event_listener.subscribe(self.on_event)
        # Re-subscribe ability charge listener(s) if reset occurred
        if reset and hasattr(self, 'ability_manager') and self.ability_manager:
            try:
                from farkle.core.game_event import GameEventType as _GET
                for a in self.ability_manager.abilities:
                    self.event_listener.subscribe(a.on_event, types={_GET.ABILITY_CHARGES_ADDED})
            except Exception:
                pass

    def _rebuild_ui_buttons(self):
        """Rebuild UI buttons to reflect new abilities (e.g., when gods level up)."""
        try:
            # Only rebuild if UI is fully initialized
            if not hasattr(self, 'ui_buttons') or not hasattr(self, 'renderer'):
                return
            
            # Remove old button sprites from sprite groups
            from farkle.ui.sprites.ui_sprites import UIButtonSprite
            if hasattr(self.renderer, 'layered'):
                for sprite in list(self.renderer.layered.sprites()):
                    if isinstance(sprite, UIButtonSprite):
                        sprite.kill()
            
            # Rebuild logical buttons
            self.ui_buttons = build_core_buttons(self)
            
            # Attach game reference to buttons
            for _btn in self.ui_buttons:
                try:
                    setattr(_btn, 'game', self)
                except Exception:
                    pass
            
            # Create new button sprites
            for btn in self.ui_buttons:
                try:
                    UIButtonSprite(btn, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
                except Exception:
                    pass
        except Exception:
            pass

    # Auto progression logic
    def on_event(self, event: GameEvent):  # type: ignore[override]
        et = event.type
        # Handle choice window events
        if et == GameEventType.REQUEST_CHOICE_CONFIRM:
            window_type = event.get("window_type")
            self.choice_window_manager.close_window(window_type)
            return
        elif et == GameEventType.REQUEST_CHOICE_SKIP:
            window_type = event.get("window_type")
            self.choice_window_manager.skip_window(window_type)
            return
        elif et == GameEventType.CHOICE_WINDOW_CLOSED:
            window_type = event.get("window_type")
            # Restore game state from CHOICE_WINDOW
            from farkle.core.game_state_enum import GameState
            if self.state_manager.get_state() == GameState.CHOICE_WINDOW:
                # Will be set to PRE_ROLL by begin_turn()
                pass
            # After god selection, start the first turn
            if window_type == "god_selection":
                try:
                    self.begin_turn(initial=True)
                except Exception:
                    pass
            # After shop closes, continue to next turn
            elif window_type == "shop":
                skipped = event.get("skipped", False)
                try:
                    self.begin_turn(from_shop=True)
                except Exception:
                    pass
            # Update choice window sprite to reflect closed state
            if self.choice_window_sprite:
                try:
                    self.choice_window_sprite.choice_window = self.choice_window_manager.get_active_window()
                    self.choice_window_sprite.sync_from_logical()
                except Exception:
                    pass
            return
        # Rebuild UI buttons when new ability is registered (e.g., god levels up)
        if et == GameEventType.ABILITY_REGISTERED:
            try:
                self._rebuild_ui_buttons()
            except Exception:
                pass
        # Detect all disasters fulfilled immediately on GOAL_FULFILLED
        if et == GameEventType.GOAL_FULFILLED:
            # Auto-switch to next unfulfilled goal if current goal was just fulfilled
            fulfilled_goal = event.get("goal")
            if fulfilled_goal:
                try:
                    current_idx = self.active_goal_index
                    if current_idx < len(self.level_state.goals) and self.level_state.goals[current_idx] == fulfilled_goal:
                        # Find next unfulfilled goal
                        next_unfulfilled_idx = None
                        for idx, g in enumerate(self.level_state.goals):
                            if not g.is_fulfilled():
                                next_unfulfilled_idx = idx
                                break
                        if next_unfulfilled_idx is not None:
                            self.active_goal_index = next_unfulfilled_idx
                except Exception:
                    pass
            
            if self.level_state._all_disasters_fulfilled() and not self.level_state.completed:
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
                
                # Auto-begin next turn if level not completed and turns remain
                if (not self.level_state.completed
                    and self.level_state.turns_left > 0
                    and self.state_manager.get_state() == self.state_manager.state.BANKED):
                    try:
                        # BEFORE calling reset_turn, check if this will be the LAST turn
                        # (i.e., after consume_turn(), turns_left will be 0)
                        will_run_out = (self.level_state.turns_left == 1)
                        
                        # Begin next turn lifecycle (consumes a turn via reset_turn)
                        self.reset_turn()
                        
                        # AFTER reset_turn, if we ran out of turns and level not complete, trigger failure
                        if (will_run_out 
                            and not self.level_state.completed 
                            and not self.level_state._all_disasters_fulfilled()):
                            if not self.level_state.failed:
                                self.level_state.failed = True
                            # Emit failure event
                            unfinished = [self.level.goals[i][0] for i in self.level_state.disaster_indices if not self.level_state.goals[i].is_fulfilled()]
                            try:
                                self.event_listener.publish(GameEvent(GameEventType.LEVEL_FAILED, payload={
                                    "level_name": self.level.name,
                                    "level_index": self.level_index,
                                    "unfinished": unfinished
                                }))
                            except Exception:
                                pass
                            # Set game state to GAME_OVER
                            try:
                                self.state_manager.set_state(self.state_manager.state.GAME_OVER)
                            except Exception:
                                pass
                    except Exception:
                        # Fallback: emit TURN_START directly if reset fails
                        try:
                            self.begin_turn(fallback=True)
                        except Exception:
                            pass
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
                # Guarantee fresh dice set for new level (avoid leftover held state from pre-shop view)
                try:
                    self._recreate_dice()
                except Exception:
                    pass
                # Refresh goal & panel sprites for new level (remove stale sprites first)
                try:
                    if hasattr(self.renderer, 'layered'):
                        # Kill existing goal sprites tied to old logical goals
                        for spr in list(self.renderer.sprite_groups.get('ui', [])):
                            if getattr(spr, 'logical', None) and spr.logical.__class__.__name__ == 'Goal':
                                spr.kill()
                        # Recreate goal + panel sprites
                        self._init_goal_and_panel_sprites()
                except Exception:
                    pass
                # Ensure button sprites re-sync (size/visibility may differ at level start)
                try:
                    from farkle.ui.sprites.ui_sprites import UIButtonSprite
                    for btn in self.ui_buttons:
                        # If sprite exists just force a sync via setting dirty flag; else create
                        spr = getattr(btn, 'sprite', None)
                        if spr and hasattr(spr, 'sync_from_logical'):
                            spr.sync_from_logical()
                        else:
                            UIButtonSprite(btn, self, self.renderer.sprite_groups['ui'], self.renderer.layered)
                except Exception:
                    pass
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
            # Only reset goal index on initial turn or when advancing to new level
            if initial or advancing:
                self.active_goal_index = 0
            self.locked_after_last_roll = False
            # Ensure dice selection flags cleared (values preserved until first roll unless reset_turn already did)
            for d in self.dice:
                d.selected = False
                d.scoring_eligible = False
            self.mark_scoring_dice()
            # Hidden flag removed; state PRE_ROLL automatically hides dice via their visible_states.
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

