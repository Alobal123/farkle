# Farkle (Event-Driven Variant)

An event-driven, multi-goal variant of Farkle implemented with Pygame. The design emphasizes clear separation of concerns:

* `Game` orchestrates input handling, high-level turn/state transitions, and publishes events.
* `DiceContainer` owns all dice objects, their lifecycle (reset/roll/mark scoring/hold), and emits dice lifecycle events.
* `Goal` objects subscribe to events and own their pending + applied scoring state.
* `Player` listens for goal fulfillment to award gold (meta progression).
* `EventListener` is a lightweight publish/subscribe hub (no external libs).
* `GameRenderer` handles all drawing and derives UI state from the immutable + pending data.

## Core Loop
1. Player rolls dice (ROLL button) – dice values update, scoring-eligible dice marked.
2. Player selects exactly one scoring combo (atomic selection constraint) and presses LOCK.
3. A `LOCK` event publishes (`goal_index`, `points`=raw combo score). The owning `Goal` accumulates raw pending points (`pending_raw`).
4. Repeat steps 1–3 any number of times (including switching active goal) in the same turn.
5. Player presses BANK – a `BANK` event causes each goal with non‑zero pending to emit `SCORE_APPLY_REQUEST`.
6. The `Player` listens to `SCORE_APPLY_REQUEST`, computes `adjusted = int(pending_raw * score_multiplier)`, and emits `SCORE_APPLIED`.
7. The goal consumes `SCORE_APPLIED`, mutates its `remaining`, and emits `GOAL_PROGRESS` / `GOAL_FULFILLED` (which in turn triggers `GOLD_GAINED`).
8. A FARKLE (rolling with no scoring options) emits `FARKLE` and all goals discard their unbanked pending.

## Event Flow Details

| Event          | Publisher            | Consumers / Effects |
|----------------|----------------------|---------------------|
| `ROLL`         | Game (future use)    | (Currently passive) |
| `LOCK`         | Game after auto-lock | Target Goal adds to `pending_raw` |
| `BANK`         | Game                 | Each Goal applies pending -> emits `GOAL_PROGRESS` / `GOAL_FULFILLED` |
| `FARKLE`       | Game                 | Goals clear `pending_raw` |
| `GOAL_PROGRESS`| Goal                 | (UI / future animation) |
| `GOAL_FULFILLED`| Goal                | Player listens -> emits `GOLD_GAINED` |
| `GOLD_GAINED`  | Player               | (UI / meta systems) |

Removed legacy events: `GOAL_APPLY_POINTS` (superseded by `SCORE_APPLY_REQUEST` / `SCORE_APPLIED`).

## Scoring & Pending Logic
* Locking never mutates a goal's actual `remaining`; it only increments `pending_raw`.
* Banking initiates an event handshake: `SCORE_APPLY_REQUEST` (Goal) -> `SCORE_APPLIED` (Player) -> subtraction + `GOAL_PROGRESS` / `GOAL_FULFILLED` (Goal).
* Score modification is performed by an ordered chain of `ScoreModifier` instances owned by the `Player`. The default (and currently only) concrete modifier is `ScoreMultiplier` (multiplicative scaling).
* During `SCORE_APPLY_REQUEST` the Player folds the chain over the raw pending score to produce the adjusted value, emits `SCORE_APPLIED`, and goals never need awareness of individual modifier types.
* A legacy-style effective multiplier is still exposed via `Player.get_score_multiplier()` for UI / logging; base multiplier growth (progression) continues to occur on `LEVEL_ADVANCE_FINISHED`.
* Farkle costs all unbanked pending (risk/reward tension maintained).

## Atomic Combo Selection
The UI enforces that exactly one scoring rule's full combo can be locked at once. Combining disjoint scoring singles (e.g., a 1 and a 5) is disallowed in a single lock; they must be locked separately, producing separate `LOCK` events. This prevents multi-combo aggregation exploits mid-turn and simplifies reasoning.

## Directory Overview
| File | Purpose |
|------|---------|
| `game.py` | High-level orchestration, input, state transitions, event publication. |
| `dice_container.py` | Encapsulated dice lifecycle + dice events (`PRE_ROLL`, `DIE_ROLLED`, `POST_ROLL`, `DIE_HELD`). |
| `goal.py` | Goal state + event reactions (pending + application). |
| `player.py` | Reward claiming on `GOAL_FULFILLED` -> emits `GOLD_GAINED`; mediates score application (`SCORE_APPLY_REQUEST` -> `SCORE_APPLIED`). |
| `actions.py` | Button action handlers extracted from `Game`. |
| `renderer.py` | All drawing + UI state derivation. |
| `scoring.py` | Scoring rule definitions (`SingleValue`, `ThreeOfAKind`, etc.). |
| `level.py` | Immutable level definition + runtime level state (no scoring application anymore). |
| `event_listener.py` | Simple pub/sub hub. |
| `game_event.py` | Event enum + dataclass. |
| `score_modifiers.py` | Pluggable score modification chain (`ScoreModifier` base + `ScoreMultiplier`). |
| `tests/` | Unit tests (logic, events, hot dice). |

## Adding a New Event
1. Add to `GameEventType`.
2. Publish from `Game` or any `GameObject`.
3. Subscribe listeners via `event_listener.subscribe(callable)`.
4. Handle in `on_event` as needed.

## Running
```
pip install -r requirements.txt  # if present, else install pygame manually
python demo.py
```

## Testing
```
python -m unittest discover -s tests -v
```

## Possible Extensions
* Visual animations for progress & fulfillment.
* Additional scoring rules (e.g., four/ five/ six-of-a-kind escalations).
* Persistent meta-progression using saved gold.
* Richer score modifier ecosystem (flat bonuses, conditional boosts, diminishing returns, temporary debuffs).
_Scoring application now event-driven (see Core Loop steps 5–7 above)._ 

---
This README reflects a fully event-driven model: no per-frame polling for level completion/failure. Score multiplier application is fully event mediated.

## DiceContainer & Dice Lifecycle Events

`DiceContainer` centralizes every mutation of dice and guarantees a strict event ordering for observability and testing.
Event ordering contract for a single roll:
1. `PRE_ROLL` (once per roll invocation, before any die value changes)
2. `DIE_ROLLED` (per die with its new face)
3. `POST_ROLL` (aggregate roll & final face values)
4. `TURN_ROLL` (logical roll phase completed; scoring dice highlighted)
Holding selected dice (during auto-lock / lock action) emits one `DIE_HELD` per die newly held.
## Level Progression Events & Player Abilities
* `LEVEL_ADVANCE_FINISHED` – Emitted after reset/subscriptions AND after new-level `TURN_START` has been sent (ordering: `LEVEL_GENERATED` -> `TURN_START` -> `LEVEL_ADVANCE_FINISHED`). Player listens here to increment its score multiplier (+0.05 per completed level after the first) replicating prior level-based scaling while remaining extensible.

These guarantees allow deterministic unit tests to assert ordering without inspecting internal state directly.

## Turn Lifecycle Events

High-level turn orchestration now emits granular hooks:

Sequence (happy path):

1. `TURN_START` – New turn begins (payload: `level`, `turns_left` after consumption for subsequent turns or `turn_index` for first level load).
2. Zero or more roll cycles:
	* `PRE_ROLL`
	* `DIE_ROLLED` (per die)
	* `POST_ROLL`
	* `TURN_ROLL` – Logical roll phase ended; scoring dice highlighted.
3. Zero or more lock operations:
	* `LOCK` (raw points added to pending) -> `TURN_LOCK_ADDED` (payload: `turn_score`).
4. Terminal action for the turn:
	* `TURN_BANKED` (after `BANK`) OR
	* `TURN_FARKLE` (after `FARKLE`).
5. `TURN_END` – Emitted exactly once with reason: one of `banked`, `farkle`, `level_complete`, `level_failed`. A level-completing bank currently uses `banked`; the subsequent level completion adds `LEVEL_COMPLETE` (without a second `TURN_END`).

These events allow UI layers or analytics/logging to animate each logical phase without querying internal Game state.

## Level Progression Events

New events decouple level advancement logic from presentation / persistence:

* `LEVEL_COMPLETE` – All mandatory goals fulfilled (published after the decisive `TURN_END` if that end was `banked`).
* `LEVEL_FAILED` – Published when turns reach zero at `TURN_END` and mandatory goals remain.
* `LEVEL_ADVANCE_STARTED` – Start of generating the next level (payload: `from_level`, `from_index`).
* `LEVEL_GENERATED` – New `Level` + `LevelState` built (payload: `new_level`, `goals`, `max_turns`). Mutation hook.
* `LEVEL_ADVANCE_FINISHED` – Emitted after reset/subscriptions AND after new-level `TURN_START` has been sent (ordering: `LEVEL_GENERATED` -> `TURN_START` -> `LEVEL_ADVANCE_FINISHED`).

Consumer Guidance:
* Save systems: listen to `LEVEL_COMPLETE` / `LEVEL_FAILED` to persist progress.
* Cinematics / transitions: start fade-out on `LEVEL_COMPLETE`, pre-render next scene during `LEVEL_GENERATED`, fade-in after `LEVEL_ADVANCE_FINISHED`.
* Dynamic rule injection: modify scoring or goals in-place at `LEVEL_GENERATED` before first turn of the new level.

### Event Ordering Summary (Selected Sequences)

Successful level end ordering (banked path):

`... TURN_BANKED` -> (`SCORE_APPLY_REQUEST` -> `SCORE_APPLIED` -> `GOAL_PROGRESS` [/`GOAL_FULFILLED`])* -> `TURN_END(reason=banked)` -> (if final fulfill completes level) `LEVEL_COMPLETE` -> `LEVEL_ADVANCE_STARTED` -> `LEVEL_GENERATED` -> `TURN_START` (new level) -> `LEVEL_ADVANCE_FINISHED`.

Failure path ordering:

`... TURN_FARKLE` (or exhausted turns) -> `TURN_END(reason=farkle)` -> `LEVEL_FAILED` -> `TURN_START` (same level reset) (no advancement events).

Guarantees:
* Exactly one `TURN_END` per turn.
* `LEVEL_COMPLETE` never precedes that turn's `TURN_END`.
* New level's `TURN_START` precedes `LEVEL_ADVANCE_FINISHED`.
* No polling; all transitions derive from events (`GOAL_FULFILLED`, `TURN_END`). Each pending goal on bank produces at most one `SCORE_APPLY_REQUEST` / `SCORE_APPLIED` pair.

## Shop & Relics System

Beginning with each completed level (after the new level's initial `TURN_START` has already fired), a between-level Shop pause inserts a `SHOP` game state that gates normal gameplay input until resolved.

High-level flow (successful or skipped purchase):

1. Previous level ends (`LEVEL_COMPLETE` path) and advancement sequence runs.
2. Ordering remains: `LEVEL_ADVANCE_STARTED` -> `LEVEL_GENERATED` -> `TURN_START` (new level) -> `LEVEL_ADVANCE_FINISHED`.
3. The `RelicManager` listens to `LEVEL_ADVANCE_FINISHED` and immediately emits:
	* `SHOP_OPENED` (shop state becomes active)
	* `RELIC_OFFERED` (currently a single offer each level)
4. While in shop state, `REQUEST_ROLL` / `REQUEST_LOCK` / `REQUEST_BANK` produce `REQUEST_DENIED` (input gating).
5. Player chooses one of:
	* Buy: UI / input layer emits `REQUEST_BUY_RELIC` -> if affordable gold -> `RELIC_PURCHASED` then `SHOP_CLOSED`.
	* Skip: emits `REQUEST_SKIP_SHOP` -> `RELIC_SKIPPED` (internal) -> `SHOP_CLOSED`.
6. On `SHOP_CLOSED`, shop state ends and normal turn actions (roll/lock/bank) are re-enabled. A new `TURN_START` is NOT emitted here (it already happened before the shop opened), preserving deterministic ordering for tests.

### Current Relic Offer Logic
For now, each level offers a single +10% score multiplier relic with a scaling cost:

```
cost = 50 + 10 * (level_index - 1)
multiplier = 1.10  # +10%
```

If purchased, the relic's modifier chain is merged with the player's when applying scores. Additional relic varieties (flat adders, conditional bonuses, diminishing returns) can be layered in by adding new `ScoreModifier` implementations and instantiating different relics.

### Combined Multiplier Math
During `SCORE_APPLY_REQUEST`, the Player aggregates its own modifier chain plus all active relic chains:

```
effective_score = pending_raw
for modifier in aggregated_modifiers:
	 effective_score = modifier.apply(effective_score, context)
```

The HUD displays a combined effective multiplier equal to the product of all `ScoreMultiplier` instances across player + relics. Example progression (ignoring other modifier types):

* Base multiplier starts at 1.00.
* Each completed level after the first adds +0.05 to the player's base multiplier (mutating the existing multiplier in place).
* Buying a +10% relic multiplies the chain by 1.10 (stacking multiplicatively).

Example: Entering level 6 you have completed 5 prior levels -> base = 1.00 + 4 * 0.05 = 1.20. Two relics purchased earlier (each 1.10) yield combined = 1.20 * 1.10 * 1.10 = 1.452. A raw score of 100 adjusts to 145 (integer truncation of 145.2).

### Shop / Relic Events Reference

| Event | When Emitted | Payload Highlights |
|-------|--------------|--------------------|
| `SHOP_OPENED` | Immediately after `LEVEL_ADVANCE_FINISHED` | `{ level_index }` |
| `RELIC_OFFERED` | After shop opens (one per level currently) | `{ name, multiplier, cost }` |
| `REQUEST_BUY_RELIC` | User intent to purchase current offer | (none) |
| `RELIC_PURCHASED` | Purchase succeeds (enough gold) | `{ name, cost, multiplier }` |
| `REQUEST_SKIP_SHOP` | User intent to skip shop | (none) |
| `RELIC_SKIPPED` | (Reserved: if explicitly emitted on skip) | (tbd) |
| `SHOP_CLOSED` | After purchase or skip | `{ skipped: bool }` |

Denied gameplay intents during shop still emit `REQUEST_DENIED` (payload contains original request type), enabling UI feedback.

### Event Ordering (Augmented Around Shop)

Successful bank causing level completion & immediate skip example:

```
... TURN_BANKED -> TURN_END(reason=banked) -> LEVEL_COMPLETE -> LEVEL_ADVANCE_STARTED -> LEVEL_GENERATED -> TURN_START(new level) -> LEVEL_ADVANCE_FINISHED -> SHOP_OPENED -> RELIC_OFFERED -> REQUEST_SKIP_SHOP -> SHOP_CLOSED -> (player may now ROLL)
```

Successful bank with relic purchase:

```
... LEVEL_ADVANCE_FINISHED -> SHOP_OPENED -> RELIC_OFFERED -> REQUEST_BUY_RELIC -> RELIC_PURCHASED -> SHOP_CLOSED -> (player may now ROLL)
```

Note the absence of an additional `TURN_START` after `SHOP_CLOSED`; gameplay resumes in the already-started first turn of the new level.

### Design Rationale
* Gating via a distinct shop phase removes race conditions where players could roll before deciding on upgrades.
* Opening the shop after the new level's `TURN_START` preserves existing test expectations about advancement ordering while still allowing a modal pause.
* Aggregated modifier chain keeps goals agnostic of meta progression sources (player vs relics).

### Future Extensions
* Multiple simultaneous relic offers (array of `RELIC_OFFERED` events with indices).
* Reroll / refresh mechanic costing gold.
* Relic rarity tiers with UI differentiation.
* Non-multiplicative modifiers (flat adders, conditional chains) for richer strategy.
* Persistence layer to save acquired relics across sessions.