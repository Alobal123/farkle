# Autosave System Documentation

## Overview
The game now features a complete autosave system that automatically saves game state and allows players to continue from where they left off.

## Features

### 1. Automatic Saving
The game automatically saves after significant events:
- **TURN_END**: After each turn completes
- **LEVEL_COMPLETE**: When a level is finished
- **GOAL_FULFILLED**: When a goal is completed
- **RELIC_PURCHASED**: When buying relics from the shop
- **SHOP_CLOSED**: When exiting the shop

### 2. Save Location
- Save file: `~/.farkle/savegame.json` (user's home directory)
- Separate from statistics file (`stats.json`)
- JSON format for easy inspection/debugging

### 3. What Gets Saved
The system saves comprehensive game state:

#### Player State
- Gold amount
- Faith points
- Temple income rate
- Active effects (blessings/curses) with remaining duration

#### Level State
- Current level index (1-based)
- Turns remaining
- Level completion/failure status
- All goals with:
  - **Complete goal definition** (name, target score, rewards, flavor text)
  - Progress (remaining/target scores)
  - Pending score
  - Reward claim status
  - Flavor text and metadata

#### Relics
- List of purchased relics (by type name)
- Automatically reactivated on load

#### Gods
- Worshipped gods list
- Each god's level and XP
- Active god index

#### Turn State
- Current turn score
- Last roll score
- Locked dice state
- Active goal index

#### Abilities
- Charges used for each ability

### 4. Menu Integration
- **Continue Button**: Appears on main menu when save exists
- **New Game Button**: Always available to start fresh
- **Statistics Button**: View cross-session statistics

### 5. Save Management
- **Auto-delete on game over**: Save cleared when returning to menu from game over screen
- **Continue from last state**: Resume exactly where you left off
- **No manual save required**: Everything happens automatically

## Architecture

### SaveManager Class
Located in `farkle/meta/save_manager.py`

**Key Methods:**
- `attach(game)`: Subscribe to game events for autosave
- `save()`: Serialize and save current game state
- `load()`: Load saved game data from disk
- `restore_game_state(game, save_data)`: Restore state into Game object
- `has_save()`: Check if save file exists
- `delete_save()`: Remove save file

**Event-Driven:**
Uses the game's event system to trigger saves automatically. Subscribes to key game events and saves state when they occur.

### Integration Points

#### App Class (`farkle/ui/screens/app.py`)
- Creates `SaveManager` instance on startup
- Checks for save file and passes status to MenuScreen
- Handles "Continue" vs "New Game" transitions
- Deletes save when returning to menu from game over

#### MenuScreen Class (`farkle/ui/screens/menu_screen.py`)
- Displays "Continue" button if `has_save=True`
- Routes to `continue_game` screen transition
- Adjusts button layout based on save existence

#### Game Class
- No changes required (uses existing event system)
- SaveManager subscribes to events after game initialization
- All state accessible through public attributes

## Usage

### For Players
1. **Starting New Game**: Click "New Game" on menu
2. **Continuing**: Click "Continue" if save exists
3. **No Manual Saving**: Game saves automatically during play
4. **Quitting**: Just close the window - progress is saved
5. **Starting Fresh**: Click "New Game" to begin a new run

### For Developers

#### Testing Autosave
```python
from farkle.meta.save_manager import SaveManager

# Create save manager with custom path for testing
save_mgr = SaveManager(save_path="test_save.json")

# Attach to game
save_mgr.attach(game)

# Manual save/load
save_mgr.save()
save_data = save_mgr.load()
save_mgr.restore_game_state(new_game, save_data)
```

#### Demo Script
Run `python demo_autosave.py` to see:
- Game state before/after save
- Restoration verification
- All checks passing

#### Unit Tests
Run `python -m pytest tests/test_autosave.py -v` for:
- 13 comprehensive test cases
- Save/load verification
- Event triggering tests
- Edge case handling

## File Format

### Example savegame.json
```json
{
  "version": "1.0",
  "player": {
    "gold": 250,
    "faith": 35,
    "temple_income": 60,
    "active_effects": [
      {
        "type": "DoubleScoreBlessing",
        "name": "Divine Fortune",
        "duration": 2
      }
    ]
  },
  "level": {
    "level_index": 4,
    "level_name": "Crisis Level",
    "turns_left": 1,
    "goals": [
      {
        "name": "Pestilence",
        "target_score": 300,
        "remaining": 100,
        "pending_raw": 0,
        "is_disaster": true,
        "reward_gold": 50,
        "reward_income": 10,
        "reward_claimed": false,
        ...
      }
    ],
    "completed": false,
    "failed": false
  },
  "relics": [
    {"name": "Charm of Fives", "type": "CharmOfFivesRelic"}
  ],
  "gods": {
    "worshipped": [
      {"name": "Zeus", "level": 3, "xp": 150}
    ],
    "active_index": 0
  },
  "turn": {
    "turn_score": 200,
    "current_roll_score": 100,
    "locked_after_last_roll": true,
    "active_goal_index": 0
  },
  "state": {
    "state": "ROLLING"
  },
  "abilities": []
}
```

## Benefits

1. **Player Experience**: Never lose progress from crashes or accidental closes
2. **Convenience**: No manual save management required
3. **Reliability**: Event-driven saves trigger at natural checkpoints
4. **Transparency**: JSON format allows debugging/inspection
5. **Separation**: Game state separate from statistics
6. **Testing**: Fully tested with comprehensive test suite

## Future Enhancements

Potential improvements:
- **Multiple save slots**: Allow multiple concurrent games
- **Cloud sync**: Save to cloud for cross-device play
- **Save metadata**: Timestamp, playtime, screenshot
- **Quick save/load**: Manual save hotkeys (F5/F9)
- **Autosave frequency**: Configurable save intervals
- **Save compression**: Reduce file size for complex states
- **Version migration**: Handle save format changes gracefully

## Notes

- **Sprite state not saved**: UI elements recreated on load (by design)
- **Event subscriptions restored**: SaveManager re-subscribes after load
- **RNG state not saved**: Each session gets fresh randomness
- **Compatible with existing games**: Works alongside current persistence system
- **No breaking changes**: Fully backward compatible
