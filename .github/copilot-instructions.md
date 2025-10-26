# Farkle - AI Coding Agent Guide

## Project Overview
Event-driven Python/Pygame Farkle variant with multi-goal system, relic shop, scoring modifiers, and sprite-based UI. Architecture emphasizes pure event flow, deterministic testing, and composable game object lifecycle.

## Core Architecture Principles

### Event-Driven State Changes
**All meaningful state transitions must emit `GameEvent` instances.** Never poll or check flags - subscribe to events via `EventListener`.

- **Central hub**: `game.event_listener` (pub/sub with optional type filtering)
- **Event ordering is critical**: Tests rely on deterministic sequences (e.g., `PRE_ROLL` → `DIE_ROLLED`* → `POST_ROLL` → `TURN_ROLL`)
- **Banking handshake**: `BANK` → `SCORE_APPLY_REQUEST` → `SCORE_APPLIED` → `TURN_END(reason=banked)`
- **Level advancement**: `LEVEL_COMPLETE` → `LEVEL_ADVANCE_STARTED` → `LEVEL_GENERATED` → `TURN_START` → `LEVEL_ADVANCE_FINISHED` → shop events

See `farkle/core/game_event.py` for event types. Check README "Event Model Overview" table for critical ordering guarantees.

### GameObject Lifecycle Hooks
All game features (relics, abilities, goals) extend `GameObject` base class (`farkle/core/game_object.py`):

```python
# Activation pattern - ALWAYS use this sequence
relic.active = False  # Start inactive
relic.activate(game)  # Triggers on_activate() hook, subscribes to events

# Deactivation pattern
relic.deactivate(game)  # Triggers on_deactivate(), unsubscribes automatically
```

**Key hooks:**
- `on_activate(game)`: Called once on inactive→active transition. Subscribe events, initialize state.
- `on_event(event)`: React to events (only called while `active=True`)
- `on_deactivate(game)`: Cleanup, emit removal events (e.g., `SCORE_MODIFIER_REMOVED`)

**Critical**: Use `emit(game, event_type, payload)` helper to publish events from objects. Never mutate global state directly.

### Scoring Pipeline (Selective Modifiers)
Scoring uses **composable per-rule modifiers** (not global multipliers):

1. **Locking**: Dice locked → `LOCK` event with `rule_key` (e.g., `"SingleValue:5"`)
2. **Pending accumulation**: Goals track `pending_raw` (unadjusted)
3. **Banking triggers**: `SCORE_APPLY_REQUEST` for each pending goal
4. **ScoringManager** (`farkle/scoring/scoring_manager.py`) applies modifier chain:
   - `FlatRuleBonus`: Adds fixed points to specific rule (e.g., +50 to `SingleValue:5`)
   - `RuleSpecificMultiplier`: Multiplies specific rule (e.g., 1.5x `ThreeOfAKind:*`)
   - `ConditionalScoreModifier`: Wraps modifiers with predicates (e.g., `MandatoryGoalOnly`)
5. **Result**: `SCORE_APPLIED` with `adjusted` total, goal updates `remaining`

**Never** modify `player.gold` or goal scores directly - emit events instead.

**Preview API**: `game.scoring_manager.preview(parts, goal=goal)` returns `{"adjusted_total": int, "parts": [...]}`

### Sprite-Based UI Rendering
All UI elements use Pygame sprite groups (`farkle/ui/sprites/`):

- **Layered rendering**: `game.renderer.layered` (z-order via `Layer` enum in `sprite_base.py`)
- **Visibility gating**: Sprites check `logical.visible_states` (set of `GameState` enums)
- **No manual draw loops**: Single `renderer.draw()` pass
- **Sprite types**: `DieSprite`, `UIButtonSprite`, `GoalSprite`, `ShopOverlaySprite`, etc.

When creating new UI: Subclass `BaseSprite`, attach to `game.renderer.sprite_groups['ui']` or appropriate group, implement `sync_from_logical()` to update visual state.

## Package Structure

```
farkle/
  core/        # Event system, GameObject base, state machine, actions
  dice/        # Die logic, DiceContainer, roll sequencing
  scoring/     # ScoringRules, ScoringManager, modifiers (FlatRuleBonus, etc.)
  goals/       # Goal tracking, pending/remaining logic
  relics/      # Relic definitions, shop lifecycle
  gods/        # God/ability management (similar to relics)
  level/       # Level generation, advancement orchestration
  players/     # Player entity (gold, HUD only)
  ui/          # Sprites, tooltips, input controller, renderer
    sprites/   # DieSprite, GoalSprite, overlays, etc.
  settings.py  # Layout constants, colors, timing
  game.py      # Composition root - wires all subsystems
```

## Developer Workflows

### Running & Testing
```powershell
# Run game (Windows PowerShell)
python demo.py

# Run all tests (pytest required)
python -m pytest -q

# Run specific test file
python -m pytest tests/test_game_logic.py -v

# Test with verbose output
python -m pytest tests/ --tb=short -q
```

### Writing Tests
**Pattern**: All tests use headless Pygame (hidden window), seed RNG for determinism:

```python
class MyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        flags = pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        cls.font = pygame.font.Font(None, 24)
        cls.clock = pygame.time.Clock()

    def setUp(self):
        self.game = Game(self.screen, self.font, self.clock, rng_seed=1)  # Seed for determinism
        # Event capture helper
        self.events = []
        self.game.event_listener.subscribe(lambda e: self.events.append(e))
```

**Assertion patterns**:
- Event ordering: `self.assertEqual(self.events[0].type, GameEventType.PRE_ROLL)`
- Scoring adjustments: `self.assertEqual(captured['adjusted'], 100)`
- Visibility: `self.assertTrue(sprite.should_draw(game))`

### Adding Relics/Modifiers

1. **Create relic class** (extend `GameObject` from relics package):
   ```python
   class MyRelic(GameObject):
       def on_activate(self, game):
           modifier = FlatRuleBonus("SingleValue:1", amount=100)
           self.emit(game, GameEventType.SCORE_MODIFIER_ADDED, {
               "relic": self.name,
               "modifier_type": "FlatRuleBonus",
               "data": {"rule_key": "SingleValue:1", "amount": 100}
           })
   ```

2. **Add to offer pool** in `RelicManager.generate_offers()`

3. **Test modifier application**:
   ```python
   def test_my_relic_bonus(self):
       # Purchase relic, lock eligible dice, bank, assert adjusted score
   ```

### Right-Click Lock Behavior
**Right-click on dice** = select + immediate lock if valid single combo:
- During `ROLLING`/`FARKLE` states only
- Must form exactly one scoring pattern (atomic constraint)
- Auto-deselects and aborts if multi-pattern selected

**Left-click** = toggle selection only (no auto-lock)

### Randomness & Seeding
Use `game.rng` (instance of `RandomSource`) for deterministic tests:
```python
game = Game(screen, font, clock, rng_seed=123)  # Reproducible rolls
```
All dice rolls, relic shuffling use `game.rng`. Pass `None` for non-deterministic gameplay.

## Critical Patterns to Follow

### ✅ DO
- Emit events for state changes: `game.event_listener.publish(GameEvent(...))`
- Use `GameObject.activate()/deactivate()` for lifecycle management
- Call `scoring_manager.preview()` for adjusted scoring projections
- Test event ordering with explicit assertions
- Leverage sprite visibility predicates (`visible_states`, `visible_predicate`)

### ❌ DON'T
- Mutate `player.gold` directly - emit `GOLD_GAINED`/`GOLD_SPENT` events
- Create polling loops - subscribe to events instead
- Use global multipliers - prefer selective per-rule modifiers
- Manually manage z-order - use sprite `Layer` enum
- Ignore test seeding - always set `rng_seed` in tests

## Common Gotchas

1. **Pending vs Applied Scores**: Goals track `pending_raw` (unadjusted locks) until banking triggers `SCORE_APPLY_REQUEST` → modifiers apply → `SCORE_APPLIED` updates `remaining`

2. **Shop Defer Pattern**: After `LEVEL_ADVANCE_FINISHED`, `_defer_turn_start=True` prevents `TURN_START` until `SHOP_CLOSED`

3. **Sprite Sync**: When logical state changes (button enabled, goal progress), call `sprite.sync_from_logical()` or set dirty flags

4. **Event Subscription Cleanup**: Always use `GameObject.deactivate()` - manual unsubscribing risks leaks

5. **Atomic Combo Rule**: Only ONE scoring pattern per lock. Multi-pattern selections (e.g., [1,5]) require separate right-clicks.

## Key Files to Reference

- **Event catalog**: `farkle/core/game_event.py` - All event types with payload schemas
- **Modifier implementations**: `farkle/scoring/score_modifiers.py` - `FlatRuleBonus`, `RuleSpecificMultiplier`, conditional wrappers
- **Test examples**: `tests/test_relic_shop.py`, `tests/test_game_logic.py` - Event ordering, modifier assertions
- **Sprite base**: `farkle/ui/sprites/sprite_base.py` - `BaseSprite`, `Layer` enum
- **Settings/layout**: `farkle/ui/settings.py` - Button rects, colors, delays

## Extending the System

**New game object (relic/ability)**:
1. Subclass `GameObject`, implement `on_activate()`, `on_deactivate()`
2. Emit modifier events on activation, removal events on deactivation
3. Add to manager's offer pool or activation list
4. Write test capturing event sequence and scoring changes

**New UI element**:
1. Create sprite subclass in `farkle/ui/sprites/`
2. Attach to appropriate sprite group (`ui`, `overlay`, `modal`)
3. Set `visible_states` or `visible_predicate` for gating
4. Implement `sync_from_logical()` for state updates

**New event type**:
1. Add to `GameEventType` enum in `game_event.py`
2. Document ordering guarantees in README
3. Subscribe handlers in relevant `GameObject.on_event()` methods
4. Add ordering test in `tests/test_events.py`
