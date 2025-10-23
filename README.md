# Farkle (Event‑Driven, Multi‑Goal Variant)

An event-driven, extensible twist on classic Farkle (Python / Pygame). Multiple simultaneous goals, selective per‑rule and global score modifiers, a between‑level relic shop, and a sprite‑first UI layer make the system highly testable and modular.

Key design pillars:
* Pure event flow for all meaningful state changes (no polling loops for progression).
* Strict dice + score lifecycle (preview vs pending vs applied are distinct phases with tests enforcing order).
* Composable modifier chain (selective rule edits + global multipliers) applied in deterministic phases.
* Explicit object lifecycle hooks (activate / deactivate) for modular feature gating (relics, abilities, temporary rules).
* Deterministic ordering guarantees enabling precise unit tests (≈100 currently passing).
* Sprite-centric rendering and gating (single pass draw; stable layering for tests and future animation).

## Quick Start
```
pip install -r requirements.txt  # or: pip install pygame
python demo.py
```

Run tests:
```
python -m pytest -q
```


## Core Gameplay Loop
1. Roll dice (ROLL) – scoring candidates are highlighted.
2. Select exactly one scoring combo (atomic constraint) then right-click to lock OR right-click a scoring die directly for select+lock.
3. Repeat: roll again, lock more combos (possibly switching active goal).
4. BANK to initiate score application handshake.
5. Optional Farkle (roll with no scoring) discards all unbanked pending.
6. Fulfill mandatory goals within allotted turns to complete the level; progression may trigger a relic shop pause.

Right-click replaces the old LOCK button entirely.

## Event Model Overview
All state transitions produce `GameEvent` instances. Selected high-level events:

| Category | Events |
|----------|--------|
| Turn | `TURN_START`, `TURN_ROLL`, `TURN_LOCK_ADDED`, `TURN_END`, `TURN_BANKED`, `TURN_FARKLE` |
| Dice | `PRE_ROLL`, `DIE_ROLLED`, `POST_ROLL`, `DIE_HELD`, `DIE_SELECTED`, `DIE_DESELECTED` |
| Scoring | `LOCK`, `SCORE_APPLY_REQUEST`, `SCORE_APPLIED`, `SCORE_MODIFIER_ADDED`, `SCORE_MODIFIER_REMOVED` |
| Goals | `GOAL_PROGRESS`, `GOAL_FULFILLED` |
| Level | `LEVEL_ADVANCE_STARTED`, `LEVEL_GENERATED`, `LEVEL_ADVANCE_FINISHED`, `LEVEL_COMPLETE`, `LEVEL_FAILED` |
| Shop | `SHOP_OPENED`, `RELIC_OFFERED`, `RELIC_PURCHASED`, `SHOP_CLOSED`, `REQUEST_BUY_RELIC`, `REQUEST_SKIP_SHOP` |
| Meta | `GOLD_GAINED`, `STATE_CHANGED`, `TARGET_SELECTION_STARTED`, `TARGET_SELECTION_FINISHED` |

Ordering guarantees (samples):
* Per roll: `PRE_ROLL` -> `DIE_ROLLED`* -> `POST_ROLL` -> `TURN_ROLL`.
* Banking path: `BANK` -> (`SCORE_APPLY_REQUEST` -> `SCORE_APPLIED`)+ -> `TURN_END(reason=banked)` -> (auto `TURN_START` of next turn if level incomplete).
* Level advancement: `TURN_END(reason=banked)` -> `LEVEL_COMPLETE` -> `LEVEL_ADVANCE_STARTED` -> `LEVEL_GENERATED` -> `TURN_START` -> `LEVEL_ADVANCE_FINISHED` -> (Shop events if any).
* Shop never emits a second `TURN_START`; gameplay resumes in the already-open turn.

## Scoring & Modifier Pipeline
Score application distinguishes raw locked points from selectively adjusted parts (global multiplier phase removed in lean scoring).

Phases:
1. Pending accumulation (`LOCK`): goals track `pending_raw` but do not mutate `remaining`.
2. Banking triggers each pending goal to emit `SCORE_APPLY_REQUEST`.
3. ScoringManager builds effective part totals (`adjusted_total`) from its modifier chain (selective rule modifiers only).
4. `SCORE_APPLIED` finalizes adjustment; goal reduces `remaining` and emits progress/fulfillment events.

Goal Pending Projection:
`Goal.projected_pending()` queries `ScoringManager.project_goal_pending(goal)` to show adjusted pending points (e.g., in tooltips or progress bars). Preview events were removed; computation is pure and synchronous.

Serialization fields (excerpt, lean): `parts`, `detailed_parts`, `total_raw`, `total_effective`, `final_global_adjusted`.

Risk: A Farkle (`FARKLE`) discards all unbanked pending, preserving tension.

## Atomic Combo Selection
Exactly one scoring pattern may be locked per `LOCK`. Multi-pattern mixes (e.g., a single 1 plus a single 5) require separate right-click locks, preventing mid-turn aggregation exploits and simplifying previews.

Right-click rules:
* On a scoring die with no active selection: select + lock if that yields a valid single combo.
* On selected scoring dice: lock immediately if selection is valid.
* On empty space: clear selection (roll/farkle states only).
* During ability targeting: right-click outside valid targets cancels selection.

### Ability Targeting (Streamlined)
Reroll ability targeting now always requires an explicit right-click confirmation (no auto-execute on first target). If a relic increases target capacity (e.g., allows 2 dice), you may:
* Select one die and finalize immediately with right-click, or
* Select a second die before finalizing.

Selection state persists until manual finalize or cancellation; tests rely on `SELECTING_TARGETS` lasting through target collection. Multi-charge scenarios clear previous targets after each execution so subsequent charges can be used without stale state.

## Tooltip System
All rich numeric/stat detail moved into delayed hover tooltips to declutter the board.
* Base delay: `TOOLTIP_DELAY_MS` (350ms). Buttons: `TOOLTIP_BUTTON_DELAY_MS` (900ms).
* Central resolver: `tooltip.resolve_hover(game, pos)`.
* Displays context-specific lines for goals, dice states, button summaries, relic offers, active relic effects, and help icon.
Adjust in `settings.py` (timings, colors). Tests demonstrate tooltip content (see hover‐related tests).

## Sprite-Based UI
Rendering has migrated to sprite subclasses (pygame `LayeredUpdates`) for deterministic z-order and simpler gating.
Current sprite coverage:
* Dice: `DieSprite`
* Buttons: `UIButtonSprite` (Next Turn appears on any Farkle. If a reroll rescue is still available, label shows "Skip Rescue" and clicking emits a `TURN_END(reason=farkle_forfeit)` followed by a `TURN_START` for the new turn; if no rescue remains it emits `TURN_START` directly.)
* Goals: `GoalSprite`
* Relic Panel: `RelicPanelSprite`
* Player HUD & Gods Panel: `PlayerHUDSprite`, `GodsPanelSprite`
* Help Icon & Rules Overlay: `HelpIconSprite`, `RulesOverlaySprite`
* Shop Overlay: `ShopOverlaySprite`

Visibility predicates live on sprites (`visible_states` / custom `visible_predicate`). Non-sprite logical objects retain state + event handling; their legacy draw methods are effectively no‑ops.

Benefits achieved:
* Deterministic layering (no manual painter’s algorithm).
* Unified update + draw pass.
* Easy future animation (`sprite.update()` hook).
* Simplified tests: assert presence/attributes instead of draw side-effects.

## Relic Shop & Progression
After each level advancement finishes (`LEVEL_ADVANCE_FINISHED`), the shop may open (`SHOP_OPENED`) offering one relic (currently a +10% multiplier) with scaling gold cost. Player chooses purchase (`REQUEST_BUY_RELIC`) or skip (`REQUEST_SKIP_SHOP`). On resolution (`SHOP_CLOSED`), normal turn actions resume.

Relics focus on selective per‑rule modifications (e.g., +50 to all `SingleValue:5` parts, +100 to `SingleValue:1`, or 1.5x to families like `ThreeOfAKind:*`). Global multipliers were removed in favor of transparent, per‑part adjustments applied centrally by the `ScoringManager` modifier chain. Tests assert modified part values to guarantee determinism.

Future expansion ideas: multiple simultaneous offers, rarity tiers, rerolling the shop, time‑limited / per‑turn relic activation, stacking diminishing returns.

### Relic Activation Lifecycle
Relics subclass `GameObject` and leverage its lifecycle:
1. Offered relics are constructed but may be (re)set to `active = False` before activation.
2. On purchase the manager forces `relic.active = False` then calls `relic.activate(game)` ensuring a fresh activation pass and event subscription.
3. On activation each relic emits a `SCORE_MODIFIER_ADDED` event per modifier it contributes. The `ScoringManager` listens and incrementally builds its modifier chain (no bulk scans on `RELIC_PURCHASED`).
4. On deactivation, relics emit `SCORE_MODIFIER_REMOVED` events allowing the manager to prune stale entries and restore original scoring behavior.

Relic string representations for the UI are assembled via `RelicManager.active_relic_lines()` producing human readable summaries (e.g., `Charm of Fives [+50 SingleValue:5]`).

#### Goal-Conditional Relics
Two relics introduce goal-scoped scoring boosts:
* `Talisman of Purpose` – +20% to all scoring parts when applying to a mandatory goal.
* `Charm of Opportunism` – +20% to all scoring parts when applying to a non-mandatory (optional) goal.

Internally they wrap a `GlobalPartsMultiplier(mult=1.2)` with `MandatoryGoalOnly` / `OptionalGoalOnly` predicates. The multiplier adjusts part values within the scoring context; absence of a goal (generic selection preview) leaves them inert.

Shop Integration: Both relics are added to the offer pool with deterministic test-friendly costs (65 and 55 gold respectively). They follow the same activation event pattern, emitting a `SCORE_MODIFIER_ADDED` for their conditional modifier on purchase.

Extensibility: Additional conditional relics can be composed by wrapping any existing modifier (e.g., `RuleSpecificMultiplier`) in a `ConditionalScoreModifier` variant.

## Architecture Overview

The codebase has been reorganized into domain‑centric packages under `farkle/`:

```
farkle/
	core/        foundational engine pieces (events, game object base, state machine, actions)
	dice/        dice + container logic and roll sequencing
	goals/       goal definitions, progress tracking
	gods/        god / ability management (selective modifiers similar to relics)
	level/       level configuration & advancement orchestration
	players/     player entity (gold economy & HUD only; scoring application centralized in ScoringManager)
	relics/      relic + relic manager (shop lifecycle, selective modifiers)
	scoring/     scoring patterns, rule keys, modifier implementations
	ui/          sprites, overlays, hud/panels, tooltip plumbing
	settings.py  global tunables (timers, colors, layout constants)
	game.py      high-level composition root (wires subsystems, bootstrap)
```

### Core Layer (`farkle/core`)
* `game_object.py` – Base class introducing explicit lifecycle: `activate(game)`, `deactivate(game)`, `on_activate(game)`, `on_event(event)`, `on_deactivate(game)`, plus `emit()` helper and visibility/interactivity predicates (legacy support for non‑sprite objects in tests).
* `event_listener.py` – Pub/sub hub supporting immediate vs queued publication. Ordering determinism is central; tests rely on it for scoring phases.
* `game_event.py` – Event enumeration + payload convenience wrapper.
* `game_state_manager.py` & `game_state_enum.py` – Simple state machine gating UI / interaction.
* `actions.py` – Input action helpers emitting request events.

### Lifecycle Hooks
Subclass responsibilities when extending `GameObject`:
* Override `on_activate(game)` for one‑time setup (e.g., subscribing extra callbacks, seeding data). Called exactly once per inactive→active transition.
* Override `on_event(event)` for reactive behavior. It will only run while `active` is True and the object remains subscribed.
* Override `on_deactivate(game)` for teardown (unregister timers, release resources). Called exactly once per active→inactive transition.
* Use `activate(game, events=None, callback=None)` to (re)wire the object. Passing `events` restricts subscription, and `callback` allows attaching an extra function tracked for auto‑unsubscribe.
* Use `deactivate(game)` to atomically flip `active=False` and remove all callbacks registered via `activate()`.
* Use `emit(game, event_type, payload)` to publish events sourced from the object.

Hooks swallow exceptions defensively (tests favor stability over failing fast in hook code); consider adding internal logging if richer diagnostics become important.

### Selective Modifier Model
Selective (per‑rule) modifiers are owned centrally by `ScoringManager` and applied during preview and finalization. Implementations (e.g., `FlatRuleBonus`, `RuleSpecificMultiplier`) live in `scoring/score_modifiers.py`. The incremental event pair (`SCORE_MODIFIER_ADDED` / `SCORE_MODIFIER_REMOVED`) lets the manager maintain an authoritative chain. Modifiers never directly mutate player/global state outside this controlled phase. Global preview events were removed to simplify the pipeline; consumers call `scoring_manager.preview()` directly and read `adjusted_total`.

#### Goal‑Conditional Modifiers
The modifier system now supports gating effects by a specific Goal context during scoring application and projection.

`ScoringManager` passes the active `goal` into the modifier context whenever computing:
* Pending application (`SCORE_APPLY_REQUEST` → `SCORE_APPLIED`)
* Goal pending projection (`Goal.projected_pending()`)
* Explicit previews that provide a goal (`scoring_manager.preview(parts, goal=goal)`)

Wrapper classes:
* `MandatoryGoalOnly(inner)` – applies `inner` modifier only if `goal.mandatory` is True.
* `OptionalGoalOnly(inner)` – applies `inner` modifier only if `goal.mandatory` is False.

Both derive from `ConditionalScoreModifier`, a generic wrapper that evaluates a predicate against the scoring context prior to invoking the inner modifier. This design lets future conditions be expressed without altering the core chain logic (e.g., fulfill‑ratio thresholds, remaining < half, pending_raw > N).

Example:
```python
from farkle.scoring.score_modifiers import RuleSpecificMultiplier, MandatoryGoalOnly

# Double the 'SingleValue:1' rule only when scoring against a mandatory goal.
mod = MandatoryGoalOnly(RuleSpecificMultiplier('SingleValue:1', mult=2.0))
game.scoring_manager.modifier_chain.add(mod)
```

Tests (`test_goal_conditional_modifiers.py`) demonstrate differential application: previews for mandatory vs optional goals yield distinct `adjusted_total` values while sharing raw parts.

Fallback behavior: If a computation has no goal (regular selection preview) conditional modifiers do not apply (predicate receives `goal=None`).

Future extension ideas:
* `FulfillmentBelow(threshold: float, inner)` – run while `(remaining / target_score) > threshold`.
* `RemainingLessThan(amount, inner)` – run once goal tightens below a point threshold.
* Compound predicates via logical operators (AND / OR wrappers) for complex gating.

All wrappers remain pure: they neither mutate goal nor parts outside invoking their inner modifier.

### Testing Philosophy
Tests assert event ordering, scoring adjustments, UI visibility, and lifecycle hook semantics. Focus tests exist for: dice roll ordering, locking invariants, modifier application, relic shop gating, tooltip content, and lifecycle (single invocation of `on_activate` / `on_deactivate`).

## Development Workflow
* Run: `python demo.py`
* Tests: `pytest -q` (focus tests exist for shop, scoring, events, tooltips, relics, selection states).
* Lint: Ruff via CI (see `.ruff.toml`) and local `ruff check .`.
* Determinism: Tests seed scenarios; avoid randomness without explicit seed for reproducibility.

### Global Randomness & Seeding
The game uses a centralized randomness wrapper `RandomSource` (`farkle/core/random_source.py`) to enable reproducible test sequences and deterministic gameplay when desired.

Instantiate a game with a seed:
```python
game = Game(screen, font, clock, rng_seed=123)
```

Effects of a provided `rng_seed`:
* Dice initial values and subsequent rolls come from `game.rng`.
* Relic offer shuffling (`RelicManager`) prefers `game.rng` for deterministic ordering (still keeping Charm of Fives first by rule).
* Reroll ability uses the seeded RNG only if a seed is set; otherwise it defers to Python's global `random` so legacy tests that monkeypatch `random.randint` continue to work.

API highlights:
* `randint(a,b)`, `choice(seq)`, `shuffle(list)`, `sample(population,k)`.
* `reseed(seed)` to swap seeds mid-run (pass `None` for fresh non-deterministic state).
* `state()` / `set_state()` for snapshot & restore in advanced tests.

Fallback behavior: If `rng_seed=None`, `game.rng` still exists but internal seed is `None`; rerolls and monkeypatched test randomness remain compatible.

## Contributing
1. Keep new features event-driven (emit + subscribe) rather than introducing polling flags.
2. Add tests for ordering-sensitive changes (especially around level advancement / shop gating).
3. Prefer adding new modifier types over special-casing inside Player.
4. Maintain sprite layering via `Layer` enum; avoid ad-hoc z-indexing.
5. Run lint & tests before PRs.

## Roadmap / Future Ideas
* Multiple concurrent relic offers + reroll mechanism.
* Rich modifier taxonomy (flat adders, conditional chains, diminishing returns, temporal buffs).
* Ability targeting animations & sprite tween utilities.
* Visual regression harness (surface snapshot diffing with seeded runs).
* Dirty rect optimization for performance.
* Structured logging replacing ad-hoc prints and silent try/excepts.
* Persistence layer (save gold, relic loadout, level index).

## License
MIT (if added). Otherwise all rights reserved by repository owner until explicit license file is present.
