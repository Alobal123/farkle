# Meta Progression System

## Overview
The meta progression system provides persistent statistics tracking across game sessions, forming the foundation for achievements, upgrades, and long-term player progression.

## Architecture

### Components

**StatisticsTracker** (`farkle/meta/statistics_tracker.py`)
- Listens to all game events via the event system
- Records relevant statistics in real-time during a single game session
- Provides summary export for display and persistence

**GameStatistics** (dataclass in `statistics_tracker.py`)
- Container for all tracked statistics from a single game session
- Separates statistics into categories: gold, farkles, scoring, gameplay

**PersistenceManager** (`farkle/meta/persistence.py`)
- Manages loading and saving statistics to disk (JSON format)
- Merges session statistics into cumulative lifetime totals
- Tracks records (highest scores, furthest level, etc.)

**PersistentStats** (dataclass in `persistence.py`)
- Container for cumulative statistics across all game sessions
- Includes lifetime totals, game counts, and personal records
- Supports backward-compatible deserialization for save file migrations

### Integration Points

1. **Game Initialization** (`farkle/game.py`)
   - StatisticsTracker created immediately after EventListener
   - Automatically subscribes to all game events
   - Available as `game.statistics_tracker`

2. **App Initialization** (`farkle/ui/screens/app.py`)
   - PersistenceManager created on app startup
   - Loads existing statistics from `~/.farkle/stats.json`
   - Available as `app.persistence`

3. **Game Over Flow** (`farkle/ui/screens/app.py`)
   - On LEVEL_FAILED event, session stats are merged into persistent storage
   - `persistence.merge_and_save()` updates lifetime totals and saves to disk
   - Statistics passed to GameOverScreen for display

4. **Game Over Screen** (`farkle/ui/screens/game_over_screen.py`)
   - Displays statistics summary at end of game
   - Shows: gold gained, farkles, total score, highest score, turns played, etc.

## Currently Tracked Statistics
## Currently Tracked Statistics

### Session Statistics (StatisticsTracker)
Tracked during a single game session:

#### Gold
- `total_gold_gained`: Cumulative gold earned
- `gold_events`: List of individual gold gain events with source tracking

#### Farkles
- `total_farkles`: Number of farkle events
- `farkle_events`: List of farkle occurrences with turn context

#### Scoring
- `total_score`: Cumulative score from all SCORE_APPLIED events
- `highest_single_score`: Largest single score application
- `score_events`: Detailed list of score applications with rule keys

#### Gameplay
- `turns_played`: Number of completed turns (tracks TURN_END events)
- `dice_rolled`: Individual dice roll events
- `relics_purchased`: Number of relics acquired
- `goals_completed`: Goals fulfilled
- `levels_completed`: Levels successfully finished

### Persistent Statistics (PersistentStats)
Cumulative across all game sessions:

#### Game Counts
- `total_games_played`: Total number of games started
- `total_games_won`: Games completed successfully
- `total_games_lost`: Games that ended in failure

#### Lifetime Totals
- `lifetime_gold_gained`: Total gold earned across all games
- `lifetime_farkles`: Total farkle events
- `lifetime_score`: Cumulative score from all sessions
- `lifetime_turns_played`: Total turns across all games
- `lifetime_dice_rolled`: Total individual dice rolled
- `lifetime_relics_purchased`: Total relics acquired
- `lifetime_goals_completed`: Total goals fulfilled
- `lifetime_levels_completed`: Total levels finished

#### Records
- `highest_single_score`: Best single scoring event ever
- `highest_game_score`: Best total score in a single game
- `most_gold_in_game`: Most gold earned in one session
- `most_turns_survived`: Longest game by turn count
- `furthest_level_reached`: Highest level/day reached

#### Meta Progression (Future Use)
- `total_meta_currency`: Currency for permanent upgrades
- `unlocked_achievements`: List of achievement IDs earned

## Usage

### Session Statistics
```python
# Get current statistics object
stats = game.statistics_tracker.get_statistics()
print(f"Gold: {stats.total_gold_gained}")
print(f"Farkles: {stats.total_farkles}")

# Get summary dictionary for display/serialization
summary = game.statistics_tracker.export_summary()

# Reset for new game session
game.statistics_tracker.reset()
```

### Persistent Statistics
```python
# Access persistence manager (created by App)
persistence = app.persistence

# Get lifetime statistics
lifetime = persistence.get_stats()
print(f"Total games played: {lifetime.total_games_played}")
print(f"Win rate: {lifetime.total_games_won / max(1, lifetime.total_games_played):.1%}")
print(f"Highest score ever: {lifetime.highest_game_score}")

# Manually merge a session (done automatically by App on game over)
session_stats = game.statistics_tracker.export_summary()
persistence.merge_and_save(
    session_stats=session_stats,
    success=False,  # or True for victory
    level_index=3   # current level/day
)

# Reset all persistent data (use with caution!)
persistence.reset()
```

### Save File Location
Statistics are saved to: `~/.farkle/stats.json`
- Windows: `C:\Users\<username>\.farkle\stats.json`
- Linux/Mac: `/home/<username>/.farkle/stats.json`

The file is automatically created on first game over and updated after each subsequent game.

### Event Tracking
The tracker automatically records these event types:
- `GOLD_GAINED` → Updates gold totals and events
- `FARKLE` → Increments farkle counter
- `SCORE_APPLIED` → Updates scoring totals and highest score
- `TURN_END` → Increments turn counter (completed turns only)
- `DIE_ROLLED` → Counts individual dice
- `RELIC_PURCHASED` → Tracks relic acquisitions
- `GOAL_FULFILLED` → Counts completed goals
- `LEVEL_COMPLETE` → Tracks level progression

## Future Extensions

### Planned Features
1. **Achievements System**
   - Use statistics to unlock achievements
   - Examples: "Roll 100 dice", "Score 1000 points in one turn", "Avoid farkle for 10 turns"
   - Display unlocked achievements on menu or game over screen

2. **Unlocks & Upgrades**
   - Spend cumulative gold on permanent upgrades
   - Unlock new relics, gods, or abilities based on achievements
   - Meta-game currency earned from achievements and milestone rewards

3. **Leaderboards & Best Runs**
   - Track personal best runs (already have highest scores)
   - Display "best run" summary on menu screen
   - Compare current session to lifetime records during gameplay

4. **Victory Screen**
   - Currently only failure screen exists
   - Victory screen should also merge and save statistics
   - Display achievement progress and unlocks earned in winning run

### Adding New Statistics
To track additional metrics:

1. Add field to `GameStatistics` dataclass:
```python
@dataclass
class GameStatistics:
    # ... existing fields ...
    new_metric: int = 0
```

2. Add event handler in `StatisticsTracker.on_event()`:
```python
elif event.type == GameEventType.NEW_EVENT:
    self.current_session.new_metric += 1
```

3. Include in `get_summary()` output:
```python
def get_summary(self):
    return {
        # ... existing categories ...
        'custom': {
            'new_metric': self.new_metric
        }
    }
```

## Testing

Tests located in `tests/test_statistics_tracker.py` cover:
- Basic event tracking for all categories
- Event accumulation and totals
- Statistics reset functionality
- Summary export format

Run tests: `python -m pytest tests/test_statistics_tracker.py -v`

## Implementation Notes

### Why Track Everything?
The statistics tracker records all events during gameplay because:
1. **Flexibility**: Unknown which metrics will be useful for future achievements
2. **Rich Data**: Detailed event logs enable complex achievement conditions
3. **Debugging**: Event sequences help diagnose game flow issues
4. **Minimal Overhead**: Event-driven architecture makes tracking essentially free

### Memory Considerations
Event lists are stored in memory during gameplay. For very long sessions:
- Consider periodic pruning of detailed event lists
- Keep running totals but drop individual events after N entries
- Implement event summary/aggregation after certain thresholds

### Determinism
Statistics tracking respects deterministic testing:
- Tests can reset tracker after game initialization
- Event-based architecture maintains deterministic ordering
- No random elements in statistics calculation
