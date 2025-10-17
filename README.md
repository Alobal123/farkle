# Farkle (Event‑Driven, Multi‑Goal Variant)

An event-driven, extensible twist on classic Farkle built with Pygame. Multiple goals, selective + global score modifiers, a between-level relic shop, and a sprite-first UI layer make the system highly testable and modular.

Key design pillars:
* Pure event flow for all meaningful state changes (no polling loops for progression).
* Strict dice + score lifecycle (preview vs pending vs applied are distinct).
* Composable modifier chain (selective rule edits + global multipliers).
* Deterministic ordering guarantees enabling precise unit tests (97 currently passing).
* Sprite-centric rendering and gating (single pass draw; easy layering).

## Quick Start
```
pip install -r requirements.txt  # or: pip install pygame
python demo.py
```

Run tests:
```
python -m pytest -q
```

Lint (Ruff):
```
pip install ruff
ruff check .
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
| Scoring | `LOCK`, `SCORE_PRE_MODIFIERS`, `SCORE_APPLY_REQUEST`, `SCORE_APPLIED` |
| Goals | `GOAL_PROGRESS`, `GOAL_FULFILLED` |
| Level | `LEVEL_ADVANCE_STARTED`, `LEVEL_GENERATED`, `LEVEL_ADVANCE_FINISHED`, `LEVEL_COMPLETE`, `LEVEL_FAILED` |
| Shop | `SHOP_OPENED`, `RELIC_OFFERED`, `RELIC_PURCHASED`, `SHOP_CLOSED`, `REQUEST_BUY_RELIC`, `REQUEST_SKIP_SHOP` |
| Meta | `GOLD_GAINED`, `STATE_CHANGED`, `TARGET_SELECTION_STARTED`, `TARGET_SELECTION_FINISHED` |

Ordering guarantees (samples):
* Per roll: `PRE_ROLL` -> `DIE_ROLLED`* -> `POST_ROLL` -> `TURN_ROLL`.
* Banking path: `BANK` -> (`SCORE_APPLY_REQUEST` -> `SCORE_PRE_MODIFIERS` -> `SCORE_APPLIED`)+ -> `TURN_END(reason=banked)` -> (auto `TURN_START` of next turn if level incomplete).
* Level advancement: `TURN_END(reason=banked)` -> `LEVEL_COMPLETE` -> `LEVEL_ADVANCE_STARTED` -> `LEVEL_GENERATED` -> `TURN_START` -> `LEVEL_ADVANCE_FINISHED` -> (Shop events if any).
* Shop never emits a second `TURN_START`; gameplay resumes in the already-open turn.

## Scoring & Modifier Pipeline
Score application distinguishes raw locked points from selectively adjusted parts and a final global multiplier phase.

Phases:
1. Pending accumulation (`LOCK`): goals track `pending_raw` but do not mutate `remaining`.
2. Banking triggers each pending goal to emit `SCORE_APPLY_REQUEST`.
3. Immediate hook `SCORE_PRE_MODIFIERS` allows gods/relics to mutate per-part values (selective modifiers).
4. Player aggregates effective part totals, applies chained global multipliers (player base multiplier + relic multipliers).
5. `SCORE_APPLIED` finalizes adjustment; goal reduces `remaining` and emits progress/fulfillment events.

Serialization fields (excerpt): `parts`, `detailed_parts`, `total_raw`, `total_effective`, `final_global_adjusted`, `multiplier`.

Risk: A Farkle (`FARKLE`) discards all unbanked pending, preserving tension.

## Atomic Combo Selection
Exactly one scoring pattern may be locked per `LOCK`. Multi-pattern mixes (e.g., a single 1 plus a single 5) require separate right-click locks, preventing mid-turn aggregation exploits and simplifying previews.

Right-click rules:
* On a scoring die with no active selection: select + lock if that yields a valid single combo.
* On selected scoring dice: lock immediately if selection is valid.
* On empty space: clear selection (roll/farkle states only).
* During ability targeting: right-click outside valid targets cancels selection.

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

Combined multiplier example:
Base 1.00 + (completed_levels_after_first * 0.05) then multiplied by each relic’s 1.10. Example: entering level 6 with four post-first completions (base 1.20) and two relics: `1.20 * 1.10 * 1.10 = 1.452` -> integer truncate -> 145 on raw 100.

Future expansion: multiple offers, rarity tiers, non-multiplicative modifiers, reroll shop.

## File & Architecture Overview
| File | Role |
|------|------|
| `game.py` | Orchestrates input, game state transitions, high-level event publication. |
| `dice_container.py` | Dice lifecycle + roll/hold events with ordering guarantees. |
| `goal.py` | Goal state, pending tracking, progress/fulfillment emissions. |
| `player.py` | Score application coordination + gold management. |
| `relic_manager.py` | Shop state & relic offer lifecycle. |
| `relic.py` | Relic definition + selective modifier hook handling. |
| `score_modifiers.py` | Modifier chain abstractions (global multiplier etc.). |
| `scoring.py` | Scoring pattern definitions. |
| `level.py` | Level config + advancement sequencing. |
| `gods_manager.py` | Ability/god selective modifier integration. |
| `actions.py` | Button action helpers (request events). |
| `renderer.py` | Layout + unified sprite pass. |
| `ui_objects.py` | Logical UI button layer (state & dynamic label). |
| `overlay_sprites.py`, `hud_sprites.py`, etc. | Sprite subclasses + sync logic. |
| `event_listener.py` | Pub/sub hub (immediate + queued dispatch). |
| `game_event.py` | Event enum & dataclass payload wrapper. |
| `settings.py` | Tunable constants (timings, colors, delays). |
| `tests/` | Comprehensive unit tests (95 passing). |

## Development Workflow
* Run: `python demo.py`
* Tests: `pytest -q` (focus tests exist for shop, scoring, events, tooltips, relics, selection states).
* Lint: Ruff via CI (see `.ruff.toml`) and local `ruff check .`.
* Determinism: Tests seed scenarios; avoid randomness without explicit seed for reproducibility.

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

---
This README reflects the current sprite-based, fully event-driven architecture (Farkle banner removed; Next Turn button now offers optional rescue forfeit) and the active test/lint tooling.
