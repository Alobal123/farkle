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
5. Player presses BANK – a `BANK` event triggers each `Goal` to apply its pending (`adjusted = pending_raw * level.score_multiplier`). Remaining goals untouched.
6. Applied subtraction emits `GOAL_PROGRESS` and, when remaining hits zero, `GOAL_FULFILLED` (which in turn drives `GOLD_GAINED` via the `Player`).
7. A FARKLE (rolling with no scoring options) emits `FARKLE` and all goals discard their unbanked pending.

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

Removed legacy events: `GOAL_APPLY_POINTS` (was intermediary before direct LOCK/BANK ownership by `Goal`).

## Scoring & Pending Logic
* Locking never mutates a goal's actual `remaining`; it only increments `pending_raw`.
* Banking converts `pending_raw` → adjusted points (multiplier applied) → subtracts from `remaining`.
* Farkle costs all unbanked pending (risk/reward tension maintained).

## Atomic Combo Selection
The UI enforces that exactly one scoring rule's full combo can be locked at once. Combining disjoint scoring singles (e.g., a 1 and a 5) is disallowed in a single lock; they must be locked separately, producing separate `LOCK` events. This prevents multi-combo aggregation exploits mid-turn and simplifies reasoning.

## Directory Overview
| File | Purpose |
|------|---------|
| `game.py` | High-level orchestration, input, state transitions, event publication. |
| `dice_container.py` | Encapsulated dice lifecycle + dice events (`PRE_ROLL`, `DIE_ROLLED`, `POST_ROLL`, `DIE_HELD`). |
| `goal.py` | Goal state + event reactions (pending + application). |
| `player.py` | Reward claiming on `GOAL_FULFILLED` -> emits `GOLD_GAINED`. |
| `actions.py` | Button action handlers extracted from `Game`. |
| `renderer.py` | All drawing + UI state derivation. |
| `scoring.py` | Scoring rule definitions (`SingleValue`, `ThreeOfAKind`, etc.). |
| `level.py` | Immutable level definition + runtime level state (no scoring application anymore). |
| `event_listener.py` | Simple pub/sub hub. |
| `game_event.py` | Event enum + dataclass. |
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
* Sound effects on events (LOCK/BANK/FARKLE/FULFILLED).

---
This README reflects a fully event-driven model: no per-frame polling for level completion/failure.

## DiceContainer & Dice Lifecycle Events

`DiceContainer` centralizes every mutation of dice and guarantees a strict event ordering for observability and testing.

Event ordering contract for a single roll:
1. `PRE_ROLL` (once per roll invocation, before any die value changes)
2. Zero or more `DIE_ROLLED` (one per non-held die whose value changes)
3. `POST_ROLL` (once, containing the list of all resulting face values including held dice)

Holding selected dice (during auto-lock / lock action) emits one `DIE_HELD` per die newly held.

Selection toggling (user clicks) emits `DIE_SELECTED` / `DIE_DESELECTED` events via the renderer-managed click handler, keeping UI concerns out of core game logic.

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

### Event Ordering Summary

Successful level end ordering (banked path):

`... TURN_BANKED` -> `TURN_END(reason=banked)` -> (Goal fulfill events) `LEVEL_COMPLETE` -> `LEVEL_ADVANCE_STARTED` -> `LEVEL_GENERATED` -> `TURN_START` (new level) -> `LEVEL_ADVANCE_FINISHED`.

Failure path ordering:

`... TURN_FARKLE` (or exhausted turns) -> `TURN_END(reason=farkle)` -> `LEVEL_FAILED` -> `TURN_START` (same level reset) (no advancement events).

Guarantees:
* Exactly one `TURN_END` per turn.
* `LEVEL_COMPLETE` never precedes that turn's `TURN_END`.
* New level's `TURN_START` precedes `LEVEL_ADVANCE_FINISHED`.
* No polling; all transitions derive from events (`GOAL_FULFILLED`, `TURN_END`).