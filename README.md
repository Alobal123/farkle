# Farkle (Event‑Driven Roguelike Variant)# Farkle (Event‑Driven Roguelike Variant)



An event-driven Farkle game (Python/Pygame) with roguelike progression: multi-goal levels, god powers, relic shop, and selective score modifiers. Architecture emphasizes pure event flow, deterministic testing, and composable game object lifecycle.An event-driven Farkle game (Python/Pygame) with roguelike progression: multi-goal levels, god powers, relic shop, and selective score modifiers. Architecture emphasizes pure event flow, deterministic testing, and composable game object lifecycle.



**Key Features:****Key Features:**

* **Event-driven architecture** - All state changes emit `GameEvent` instances (no polling)* **Event-driven architecture** - All state changes emit `GameEvent` instances (no polling)

* **Multi-goal system** - Mandatory and optional goals with different scoring strategies* **Multi-goal system** - Mandatory and optional goals with different scoring strategies

* **God powers** - Choose gods that level up and grant passive bonuses* **God powers** - Choose gods that level up and grant passive bonuses

* **Relic shop** - Between-level shop with scoring modifiers and special abilities* **Relic shop** - Between-level shop with scoring modifiers and special abilities

* **Sprite-based UI** - Layered rendering with visibility predicates and tooltips* **Sprite-based UI** - Layered rendering with visibility predicates and tooltips

* **Deterministic testing** - 260+ tests with reproducible RNG seeding* **Deterministic testing** - 260+ tests with reproducible RNG seeding



## Quick Start## Quick Start

```bash```bash

pip install pygamepip install pygame

python demo.pypython demo.py

``````



Run tests:Run tests:

```bash```bash

python -m pytest -qpython -m pytest -q

``````



## Gameplay## Gameplay



**Core Loop:****Core Loop:**

1. **Roll** - Dice show scoring candidates1. **Roll** - Dice show scoring candidates

2. **Lock** - Right-click a die or selected combo to lock (must be exactly one scoring pattern)2. **Lock** - Right-click a die or selected combo to lock (must be exactly one scoring pattern)

3. **Repeat** - Roll unlocked dice, lock more combos3. **Repeat** - Roll unlocked dice, lock more combos

4. **Bank** - Apply pending scores to active goal and end turn4. **Bank** - Apply pending scores to active goal and end turn

5. **Farkle risk** - Rolling with no scoring options discards all pending points5. **Farkle risk** - Rolling with no scoring options discards all pending points



**Progression:****Progression:**

- Complete mandatory goals within turn limits to advance levels- Complete mandatory goals within turn limits to advance levels

- After each level, visit the relic shop to purchase scoring modifiers- After each level, visit the relic shop to purchase scoring modifiers

- Choose gods that level up as you complete goals, granting passive bonuses- Choose gods that level up as you complete goals, granting passive bonuses

- Earn gold by banking points to buy relics and unlock powerful combos- Earn gold by banking points to buy relics and unlock powerful combos



## Architecture## Architecture



### Event-Driven State Changes### Event-Driven State Changes

All meaningful state transitions emit `GameEvent` instances via `game.event_listener` (pub/sub hub).All meaningful state transitions emit `GameEvent` instances via `game.event_listener` (pub/sub hub).



**Key Event Types:****Key Event Types:**

- **Turn:** `TURN_START`, `TURN_ROLL`, `TURN_END`, `TURN_BANKED`, `TURN_FARKLE`- **Turn:** `TURN_START`, `TURN_ROLL`, `TURN_END`, `TURN_BANKED`, `TURN_FARKLE`

- **Dice:** `PRE_ROLL`, `DIE_ROLLED`, `POST_ROLL`, `DIE_SELECTED`- **Dice:** `PRE_ROLL`, `DIE_ROLLED`, `POST_ROLL`, `DIE_SELECTED`

- **Scoring:** `LOCK`, `SCORE_APPLY_REQUEST`, `SCORE_APPLIED`, `SCORE_MODIFIER_ADDED`- **Scoring:** `LOCK`, `SCORE_APPLY_REQUEST`, `SCORE_APPLIED`, `SCORE_MODIFIER_ADDED`

- **Goals:** `GOAL_PROGRESS`, `GOAL_FULFILLED`- **Goals:** `GOAL_PROGRESS`, `GOAL_FULFILLED`

- **Level:** `LEVEL_COMPLETE`, `LEVEL_ADVANCE_STARTED`, `LEVEL_ADVANCE_FINISHED`- **Level:** `LEVEL_COMPLETE`, `LEVEL_ADVANCE_STARTED`, `LEVEL_ADVANCE_FINISHED`

- **Shop:** `CHOICE_WINDOW_OPENED`, `CHOICE_WINDOW_CLOSED`, `RELIC_PURCHASED`- **Shop:** `CHOICE_WINDOW_OPENED`, `CHOICE_WINDOW_CLOSED`, `RELIC_PURCHASED`

- **Gods:** `GOD_SELECTED`, `GOD_LEVEL_UP`- **Gods:** `GOD_SELECTED`, `GOD_LEVEL_UP`



**Critical Ordering Guarantees:****Critical Ordering Guarantees:**

- Roll: `PRE_ROLL` → `DIE_ROLLED`* → `POST_ROLL` → `TURN_ROLL`- Roll: `PRE_ROLL` → `DIE_ROLLED`* → `POST_ROLL` → `TURN_ROLL`

- Bank: `BANK` → `SCORE_APPLY_REQUEST` → `SCORE_APPLIED` → `TURN_END(banked)` → auto `TURN_START`- Bank: `BANK` → `SCORE_APPLY_REQUEST` → `SCORE_APPLIED` → `TURN_END(banked)` → auto `TURN_START`

- Level advancement: `LEVEL_COMPLETE` → `LEVEL_ADVANCE_STARTED` → `LEVEL_GENERATED` → `TURN_START` → `LEVEL_ADVANCE_FINISHED` → shop events- Level advancement: `LEVEL_COMPLETE` → `LEVEL_ADVANCE_STARTED` → `LEVEL_GENERATED` → `TURN_START` → `LEVEL_ADVANCE_FINISHED` → shop events



### Scoring Pipeline### Scoring Pipeline

Score application uses **composable per-rule modifiers** (not global multipliers):Score application uses **composable per-rule modifiers** (not global multipliers):



1. **Locking:** Selected dice → `LOCK` event with `rule_key` (e.g., `"SingleValue:5"`)1. **Locking:** Selected dice → `LOCK` event with `rule_key` (e.g., `"SingleValue:5"`)

2. **Pending accumulation:** Goals track `pending_raw` (unadjusted base points)2. **Pending accumulation:** Goals track `pending_raw` (unadjusted base points)

3. **Banking:** Emits `SCORE_APPLY_REQUEST` for active goal3. **Banking:** Emits `SCORE_APPLY_REQUEST` for active goal

4. **Modifier chain:** `ScoringManager` applies modifiers in order:4. **Modifier chain:** `ScoringManager` applies modifiers in order:

   - `FlatRuleBonus`: Adds fixed points to specific rules (+50 to `SingleValue:5`)   - `FlatRuleBonus`: Adds fixed points to specific rules (+50 to `SingleValue:5`)

   - `RuleSpecificMultiplier`: Multiplies specific rules (1.5x `ThreeOfAKind:*`)   - `RuleSpecificMultiplier`: Multiplies specific rules (1.5x `ThreeOfAKind:*`)

   - `ConditionalScoreModifier`: Applies modifiers based on goal type (mandatory vs optional)   - `ConditionalScoreModifier`: Applies modifiers based on goal type (mandatory vs optional)

5. **Result:** `SCORE_APPLIED` event with `adjusted` total, goal updates `remaining`5. **Result:** `SCORE_APPLIED` event with `adjusted` total, goal updates `remaining`



**Preview API:** `game.scoring_manager.preview(parts, goal=goal)` returns adjusted totals without mutation.**Preview API:** `game.scoring_manager.preview(parts, goal=goal)` returns adjusted totals without mutation.



### GameObject Lifecycle### GameObject Lifecycle

All game features (relics, abilities, gods) extend `GameObject` base class with explicit lifecycle hooks:All game features (relics, abilities, gods) extend `GameObject` base class with explicit lifecycle hooks:



```python```python

# Activation pattern# Activation pattern

relic.active = False  # Start inactiverelic.active = False  # Start inactive

relic.activate(game)  # Triggers on_activate() hook, subscribes to eventsrelic.activate(game)  # Triggers on_activate() hook, subscribes to events



# Deactivation# Deactivation

relic.deactivate(game)  # Triggers on_deactivate(), unsubscribes automaticallyrelic.deactivate(game)  # Triggers on_deactivate(), unsubscribes automatically

``````



**Lifecycle Hooks:****Lifecycle Hooks:**

- `on_activate(game)`: One-time setup, subscribe to events, initialize state- `on_activate(game)`: One-time setup, subscribe to events, initialize state

- `on_event(event)`: React to events (only called while `active=True`)- `on_event(event)`: React to events (only called while `active=True`)

- `on_deactivate(game)`: Cleanup, emit removal events (e.g., `SCORE_MODIFIER_REMOVED`)- `on_deactivate(game)`: Cleanup, emit removal events (e.g., `SCORE_MODIFIER_REMOVED`)



Use `emit(game, event_type, payload)` helper to publish events from objects.Use `emit(game, event_type, payload)` helper to publish events from objects.



### Sprite-Based UI### Sprite-Based UI

All UI elements use Pygame sprite groups with layered rendering:All UI elements use Pygame sprite groups with layered rendering:



- **Layered rendering:** `game.renderer.layered` with z-order via `Layer` enum- **Layered rendering:** `game.renderer.layered` with z-order via `Layer` enum

- **Visibility gating:** Sprites check `visible_states` (set of `GameState` enums)- **Visibility gating:** Sprites check `visible_states` (set of `GameState` enums)

- **Single draw pass:** No manual loops, sprites auto-render based on layer- **Single draw pass:** No manual loops, sprites auto-render based on layer

- **Sprite types:** `DieSprite`, `UIButtonSprite`, `GoalSprite`, `RelicPanelSprite`, `ChoiceWindowSprite`, etc.- **Sprite types:** `DieSprite`, `UIButtonSprite`, `GoalSprite`, `RelicPanelSprite`, `ChoiceWindowSprite`, etc.

- **Tooltip system:** Delayed hover tooltips (350ms base, 900ms for buttons) via `tooltip.resolve_hover(game, pos)`- **Tooltip system:** Delayed hover tooltips (350ms base, 900ms for buttons) via `tooltip.resolve_hover(game, pos)`



New UI elements subclass `BaseSprite`, set `visible_states` or `visible_predicate`, implement `sync_from_logical()` for state updates.New UI elements subclass `BaseSprite`, set `visible_states` or `visible_predicate`, implement `sync_from_logical()` for state updates.



## Game Systems## Game Systems



### Relic Shop### Relic Shop

After each level, a choice window opens offering relics for purchase with gold:After each level, a choice window opens offering relics for purchase with gold:



- **Modifier types:** Flat bonuses (+50 to `SingleValue:5`), multipliers (1.5x `ThreeOfAKind:*`), conditional effects (bonus only for mandatory/optional goals)## Atomic Combo Selection

- **Lifecycle:** Relics emit `SCORE_MODIFIER_ADDED` on activation, `SCORE_MODIFIER_REMOVED` on deactivationExactly one scoring pattern may be locked per `LOCK`. Multi-pattern mixes (e.g., a single 1 plus a single 5) require separate right-click locks, preventing mid-turn aggregation exploits and simplifying previews.

- **Examples:** Charm of Fives (+50 to fives), Talisman of Purpose (+20% for mandatory goals), Extra Reroll (additional reroll charge)

Right-click rules:

### God System* On a scoring die with no active selection: select + lock if that yields a valid single combo.

Choose up to 3 gods at game start. Gods level up by tracking specific events:* On selected scoring dice: lock immediately if selection is valid.

* On empty space: clear selection (roll/farkle states only).

- **Ares (Warfare):** Tracks combat-category goals, grants damage bonuses* During ability targeting: right-click outside valid targets cancels selection.

- **Hermes (Travel):** Tracks travel-category goals, grants movement bonuses  

- **Hades (Mystery):** Tracks mystery-category goals, grants arcane bonuses### Ability Targeting (Streamlined)

- **Demeter (Harvest):** Tracks harvest-category goals, grants resource bonusesReroll ability targeting now always requires an explicit right-click confirmation (no auto-execute on first target). If a relic increases target capacity (e.g., allows 2 dice), you may:

* Select one die and finalize immediately with right-click, or

Gods gain progress on relevant goal completions and emit `GOD_LEVEL_UP` events. Serialization preserves god class type, level, and progress for save/load.* Select a second die before finalizing.



### Ability SystemSelection state persists until manual finalize or cancellation; tests rely on `SELECTING_TARGETS` lasting through target collection. Multi-charge scenarios clear previous targets after each execution so subsequent charges can be used without stale state.

Gods grant reroll abilities with explicit targeting:

## Tooltip System

1. Click ability button → enters `SELECTING_TARGETS` stateAll rich numeric/stat detail moved into delayed hover tooltips to declutter the board.

2. Left-click dice to select (up to capacity, e.g., 2 dice for upgraded relics)* Base delay: `TOOLTIP_DELAY_MS` (350ms). Buttons: `TOOLTIP_BUTTON_DELAY_MS` (900ms).

3. Right-click to confirm and execute reroll* Central resolver: `tooltip.resolve_hover(game, pos)`.

4. Multi-charge abilities clear targets between uses* Displays context-specific lines for goals, dice states, button summaries, relic offers, active relic effects, and help icon.

Adjust in `settings.py` (timings, colors). Tests demonstrate tooltip content (see hover‐related tests).

## Package Structure

## Sprite-Based UI

```Rendering has migrated to sprite subclasses (pygame `LayeredUpdates`) for deterministic z-order and simpler gating.

farkle/Current sprite coverage:

  core/        # Event system, GameObject base, state machine, actions* Dice: `DieSprite`

  dice/        # Die logic, DiceContainer, roll sequencing* Buttons: `UIButtonSprite` (Next Turn appears on any Farkle. If a reroll rescue is still available, label shows "Skip Rescue" and clicking emits a `TURN_END(reason=farkle_forfeit)` followed by a `TURN_START` for the new turn; if no rescue remains it emits `TURN_START` directly.)

  scoring/     # ScoringRules, ScoringManager, modifiers (FlatRuleBonus, etc.)* Goals: `GoalSprite`

  goals/       # Goal tracking, pending/remaining logic* Relic Panel: `RelicPanelSprite`

  relics/      # Relic definitions, shop lifecycle* Player HUD & Gods Panel: `PlayerHUDSprite`, `GodsPanelSprite`

  gods/        # God/ability management, CategoryGod base class* Help Icon & Rules Overlay: `HelpIconSprite`, `RulesOverlaySprite`

  level/       # Level generation, advancement orchestration* Shop Overlay: `ShopOverlaySprite`

  players/     # Player entity (gold, HUD only)

  meta/        # Save/load system with god serializationVisibility predicates live on sprites (`visible_states` / custom `visible_predicate`). Non-sprite logical objects retain state + event handling; their legacy draw methods are effectively no‑ops.

  ui/          # Sprites, tooltips, input controller, renderer

    screens/   # MenuScreen, GameScreen, GameOverScreen, StatisticsScreen, App controllerBenefits achieved:

    sprites/   # DieSprite, GoalSprite, ChoiceWindowSprite, overlays, etc.* Deterministic layering (no manual painter’s algorithm).

  settings.py  # Layout constants, colors, timing* Unified update + draw pass.

  game.py      # Composition root - wires all subsystems* Easy future animation (`sprite.update()` hook).

```* Simplified tests: assert presence/attributes instead of draw side-effects.



## Development## Relic Shop & Progression

After each level advancement finishes (`LEVEL_ADVANCE_FINISHED`), the shop may open (`SHOP_OPENED`) offering one relic (currently a +10% multiplier) with scaling gold cost. Player chooses purchase (`REQUEST_BUY_RELIC`) or skip (`REQUEST_SKIP_SHOP`). On resolution (`SHOP_CLOSED`), normal turn actions resume.

### Running & Testing

```bashRelics focus on selective per‑rule modifications (e.g., +50 to all `SingleValue:5` parts, +100 to `SingleValue:1`, or 1.5x to families like `ThreeOfAKind:*`). Global multipliers were removed in favor of transparent, per‑part adjustments applied centrally by the `ScoringManager` modifier chain. Tests assert modified part values to guarantee determinism.

# Run game

python demo.pyFuture expansion ideas: multiple simultaneous offers, rarity tiers, rerolling the shop, time‑limited / per‑turn relic activation, stacking diminishing returns.



# Run all tests### Relic Shop

python -m pytest -qAfter each level, a choice window opens offering relics for purchase with gold:



# Run specific test file- **Modifier types:** Flat bonuses (+50 to `SingleValue:5`), multipliers (1.5x `ThreeOfAKind:*`), conditional effects (bonus only for mandatory/optional goals)

python -m pytest tests/test_game_logic.py -v- **Lifecycle:** Relics emit `SCORE_MODIFIER_ADDED` on activation, `SCORE_MODIFIER_REMOVED` on deactivation

```- **Examples:** Charm of Fives (+50 to fives), Talisman of Purpose (+20% for mandatory goals), Extra Reroll (additional reroll charge)



### Deterministic Testing### God System

All tests use seeded RNG for reproducibility:Choose up to 3 gods at game start. Gods level up by tracking specific events:



```python- **Ares (Warfare):** Tracks combat-category goals, grants damage bonuses

game = Game(screen, font, clock, rng_seed=1)  # Reproducible rolls- **Hermes (Travel):** Tracks travel-category goals, grants movement bonuses  

```- **Hades (Mystery):** Tracks mystery-category goals, grants arcane bonuses

- **Demeter (Harvest):** Tracks harvest-category goals, grants resource bonuses

The `RandomSource` wrapper (`farkle/core/random_source.py`) provides `randint()`, `choice()`, `shuffle()`, etc. Pass `rng_seed=None` for non-deterministic gameplay.

Gods gain progress on relevant goal completions and emit `GOD_LEVEL_UP` events. Serialization preserves god class type, level, and progress for save/load.

### Writing Tests

Event ordering is critical. Tests capture events and assert sequences:### Ability System

Gods grant reroll abilities with explicit targeting:

```python

def test_bank_flow(self):1. Click ability button → enters `SELECTING_TARGETS` state

    # Capture events2. Left-click dice to select (up to capacity, e.g., 2 dice for upgraded relics)

    events = []3. Right-click to confirm and execute reroll

    game.event_listener.subscribe(lambda e: events.append(e))4. Multi-charge abilities clear targets between uses

    

    # ... trigger actions ...## Package Structure

    

    # Assert ordering```

    self.assertEqual(events[0].type, GameEventType.BANK)farkle/

    self.assertEqual(events[1].type, GameEventType.SCORE_APPLY_REQUEST)  core/        # Event system, GameObject base, state machine, actions

    self.assertEqual(events[2].type, GameEventType.SCORE_APPLIED)  dice/        # Die logic, DiceContainer, roll sequencing

```  scoring/     # ScoringRules, ScoringManager, modifiers (FlatRuleBonus, etc.)

  goals/       # Goal tracking, pending/remaining logic

### Best Practices  relics/      # Relic definitions, shop lifecycle

1. **Event-driven changes** - Emit events for state changes, don't poll flags  gods/        # God/ability management, CategoryGod base class

2. **Selective modifiers** - Use per-rule modifiers over global multipliers  level/       # Level generation, advancement orchestration

3. **GameObject lifecycle** - Use `activate()`/`deactivate()` for feature gating  players/     # Player entity (gold, HUD only)

4. **Sprite layering** - Use `Layer` enum, avoid manual z-indexing  meta/        # Save/load system with god serialization

5. **Test seeding** - Always set `rng_seed` in tests for determinism  ui/          # Sprites, tooltips, input controller, renderer

    screens/   # MenuScreen, GameScreen, GameOverScreen, StatisticsScreen, App controller

## Contributing    sprites/   # DieSprite, GoalSprite, ChoiceWindowSprite, overlays, etc.

Keep new features event-driven (emit + subscribe), add tests for ordering-sensitive changes, prefer modifier types over special-casing, maintain sprite layering via `Layer` enum.  settings.py  # Layout constants, colors, timing

  game.py      # Composition root - wires all subsystems

## License```

MIT (if added). Otherwise all rights reserved by repository owner.

## Development

### Running & Testing
```bash
# Run game
python demo.py

# Run all tests
python -m pytest -q

# Run specific test file
python -m pytest tests/test_game_logic.py -v
```

### Deterministic Testing
All tests use seeded RNG for reproducibility:

```python
game = Game(screen, font, clock, rng_seed=1)  # Reproducible rolls
```

The `RandomSource` wrapper (`farkle/core/random_source.py`) provides `randint()`, `choice()`, `shuffle()`, etc. Pass `rng_seed=None` for non-deterministic gameplay.

### Writing Tests
Event ordering is critical. Tests capture events and assert sequences:

```python
def test_bank_flow(self):
    # Capture events
    events = []
    game.event_listener.subscribe(lambda e: events.append(e))
    
    # ... trigger actions ...
    
    # Assert ordering
    self.assertEqual(events[0].type, GameEventType.BANK)
    self.assertEqual(events[1].type, GameEventType.SCORE_APPLY_REQUEST)
    self.assertEqual(events[2].type, GameEventType.SCORE_APPLIED)
```

### Best Practices
1. **Event-driven changes** - Emit events for state changes, don't poll flags
2. **Selective modifiers** - Use per-rule modifiers over global multipliers
3. **GameObject lifecycle** - Use `activate()`/`deactivate()` for feature gating
4. **Sprite layering** - Use `Layer` enum, avoid manual z-indexing
5. **Test seeding** - Always set `rng_seed` in tests for determinism

## Contributing
Keep new features event-driven (emit + subscribe), add tests for ordering-sensitive changes, prefer modifier types over special-casing, maintain sprite layering via `Layer` enum.

## License
MIT (if added). Otherwise all rights reserved by repository owner.
