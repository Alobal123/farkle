# Meta Progression System - Statistics Tracker

## Overview
The statistics tracker is a foundational component for implementing meta progression features like achievements, upgrades, and persistent player progress across games.

## Architecture

### Components

**StatisticsTracker** (`farkle/meta/statistics_tracker.py`)
- Listens to all game events via the event system
- Records relevant statistics in real-time
- Provides summary export for display and persistence

**GameStatistics** (dataclass in `statistics_tracker.py`)
- Container for all tracked statistics from a single game session
- Separates statistics into categories: gold, farkles, scoring, gameplay

### Integration Points

1. **Game Initialization** (`farkle/game.py`)
   - StatisticsTracker created immediately after EventListener
   - Automatically subscribes to all game events
   - Available as `game.statistics_tracker`

2. **Game Over Screen** (`farkle/ui/screens/game_over_screen.py`)
   - Displays statistics summary at end of game
   - Shows: gold gained, farkles, total score, highest score, turns played, etc.

3. **App Controller** (`farkle/ui/screens/app.py`)
   - Passes statistics to GameOverScreen on level failure
   - Retrieves summary via `game.statistics_tracker.export_summary()`

## Currently Tracked Statistics

### Gold
- `total_gold_gained`: Cumulative gold earned
- `gold_events`: List of individual gold gain events with source tracking

### Farkles
- `total_farkles`: Number of farkle events
- `farkle_events`: List of farkle occurrences with turn context

### Scoring
- `total_score`: Cumulative score from all SCORE_APPLIED events
- `highest_single_score`: Largest single score application
- `score_events`: Detailed list of score applications with rule keys

### Gameplay
- `turns_played`: Number of completed turns (tracks TURN_END events)
- `dice_rolled`: Individual dice roll events
- `relics_purchased`: Number of relics acquired
- `goals_completed`: Goals fulfilled
- `levels_completed`: Levels successfully finished

## Usage

### Accessing Statistics
```python
# Get current statistics object
stats = game.statistics_tracker.get_statistics()
print(f"Gold: {stats.total_gold_gained}")
print(f"Farkles: {stats.total_farkles}")

# Get summary dictionary for display/serialization
summary = game.statistics_tracker.export_summary()
```

### Resetting Statistics
```python
# Reset for new game session
game.statistics_tracker.reset()
```

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

2. **Persistent Progression**
   - Save statistics across game sessions
   - Track lifetime statistics (JSON/SQLite)
   - Career totals and records

3. **Unlocks & Upgrades**
   - Spend cumulative gold on permanent upgrades
   - Unlock new relics, gods, or abilities
   - Meta-game currency earned from achievements

4. **Leaderboards**
   - Track high scores and best runs
   - Compare statistics with previous sessions

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
