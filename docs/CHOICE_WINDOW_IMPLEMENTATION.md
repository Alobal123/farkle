# Choice Window System - Implementation Summary

## Overview

Successfully implemented a general-purpose choice window system that can be used for god selection, relic shops, and any future selection screens. The key feature is the **minimize/maximize functionality** that allows players to inspect the game state before making decisions.

## What Was Created

### Core Components

1. **`farkle/ui/choice_window.py`** (172 lines)
   - `ChoiceWindow` - Main window class with state management
   - `ChoiceItem` - Generic selectable item container
   - `ChoiceWindowState` - Enum for window states (CLOSED, MAXIMIZED, MINIMIZED)

2. **`farkle/ui/choice_window_manager.py`** (114 lines)
   - `ChoiceWindowManager` - Manages window lifecycle and event emission
   - Handles open/close/skip operations
   - Executes selection callbacks

3. **`farkle/ui/sprites/choice_window_sprite.py`** (386 lines)
   - `ChoiceWindowSprite` - Main window rendering
   - `ChoiceItemSprite` - Individual item card rendering
   - Handles minimize/maximize UI
   - Processes mouse clicks

4. **Event Types** (added to `farkle/core/game_event.py`)
   - `CHOICE_WINDOW_OPENED`
   - `CHOICE_WINDOW_CLOSED`
   - `CHOICE_WINDOW_MINIMIZED`
   - `CHOICE_WINDOW_MAXIMIZED`
   - `CHOICE_ITEM_SELECTED`
   - `REQUEST_CHOICE_CONFIRM`
   - `REQUEST_CHOICE_SKIP`

### Documentation & Examples

5. **`docs/CHOICE_WINDOW.md`** - Comprehensive documentation
   - Architecture overview
   - Usage examples (god selection, shop, events)
   - Event flow diagram
   - Migration guide from old shop system
   - Design rationale

6. **`examples/choice_window_demo.py`** - Practical examples
   - God selection implementation
   - Relic shop implementation
   - Random event implementation
   - Event handling patterns

7. **`tests/test_choice_window.py`** - 9 comprehensive tests
   - Window creation and state management
   - Open/close/minimize/maximize behavior
   - Single and multiple selection modes
   - Manager integration
   - Event emission

## Key Features

### 1. Minimize/Maximize Functionality

The standout feature that sets this apart from the old shop system:

- **Minimized State**: Small icon in bottom-right corner showing window title
- **Maximized State**: Full window with items, buttons, and controls
- **Toggle**: Click minimize button or minimized icon to switch states
- **Background Visibility**: Semi-transparent overlay allows seeing game state

This allows players to:
1. Open a selection screen (e.g., shop)
2. Minimize it to inspect current state (gold, relics, goals)
3. Maximize and make an informed decision

### 2. Flexible Selection Modes

- **Single Selection**: Choose 1 item (god selection, shop purchases)
- **Multiple Selection**: Choose N items (selecting multiple gods)
- **Min/Max Constraints**: Enforce selection requirements
- **Optional Skip**: Allow skipping without selection

### 3. Cost-Based Availability

- Items can be enabled/disabled based on cost
- Visual indication (grayed out + "Unavailable" button)
- Prevents invalid selections

### 4. Event-Driven Design

All interactions emit events:
- Clean separation of concerns
- Easy to test and extend
- Follows existing game architecture

## Testing Results

**All tests passing: 252 tests (including 9 new choice window tests)**

New tests cover:
- ✅ Basic window creation
- ✅ Open/close lifecycle
- ✅ Minimize/maximize transitions
- ✅ Single item selection
- ✅ Multiple item selection
- ✅ Selection validation
- ✅ Manager integration
- ✅ Event emission
- ✅ Callback execution

## How It Works

### UI Behavior

**Maximized State:**
```
┌─────────────────────────────────────────────────┐
│ [Title]                              [Minimize] │
│                                                  │
│  ┌──────┐  ┌──────┐  ┌──────┐                  │
│  │Item 1│  │Item 2│  │Item 3│                  │
│  │Name  │  │Name  │  │Name  │                  │
│  │Desc  │  │Desc  │  │Desc  │                  │
│  │Cost  │  │Cost  │  │Cost  │                  │
│  │[Sel] │  │[Sel] │  │[Sel] │                  │
│  └──────┘  └──────┘  └──────┘                  │
│                                                  │
│           [Confirm]  [Skip]                     │
└─────────────────────────────────────────────────┘
```

**Minimized State:**
```
                                    ┌──────────────┐
                                    │ [Title]      │
                                    │ (Click...)   │
                                    └──────────────┘
```

### Event Flow

```
Player Action → Event → Handler → Callback → State Change → Sprite Update
```

Example for purchasing a relic:
1. Player clicks "Select" on a relic
2. `CHOICE_ITEM_SELECTED` event emitted
3. Window adds item to selected_indices
4. Player clicks "Confirm"
5. `REQUEST_CHOICE_CONFIRM` event emitted
6. Manager calls item's `on_select` callback
7. Gold deducted, relic acquired
8. `CHOICE_WINDOW_CLOSED` event emitted
9. Window state → CLOSED
10. Sprite updates (becomes transparent)

## Usage Pattern

### Basic Setup (in Game)

```python
from farkle.ui.choice_window_manager import ChoiceWindowManager

# In Game.__init__:
self.choice_window_manager = ChoiceWindowManager(self)

# Subscribe to events:
self.event_listener.subscribe(self._handle_choice_events)
```

### Creating a Window

```python
from farkle.ui.choice_window import ChoiceWindow, ChoiceItem

items = [
    ChoiceItem(
        id="unique_id",
        name="Display Name",
        description="Short description",
        payload=actual_object,
        on_select=callback_function,
        cost=100,  # Optional
        enabled=True,  # Optional
        effect_text="Detailed effect"  # Optional
    )
]

window = ChoiceWindow(
    title="Window Title",
    items=items,
    window_type="identifier",
    allow_skip=True,
    allow_minimize=True,
    min_selections=0,
    max_selections=1
)

game.choice_window_manager.open_window(window)
```

### Handling Events

```python
def _handle_choice_events(self, event):
    if event.type == GameEventType.REQUEST_CHOICE_CONFIRM:
        self.choice_window_manager.close_window()
    
    elif event.type == GameEventType.REQUEST_CHOICE_SKIP:
        self.choice_window_manager.skip_window()
    
    elif event.type == GameEventType.CHOICE_WINDOW_CLOSED:
        # Post-closure logic
        window_type = event.get("window_type")
        if window_type == "shop":
            self.begin_turn(from_shop=True)
```

## Next Steps for Integration

To use this system for the shop and god selection:

### 1. Replace Shop System

Replace the current `ShopOverlaySprite` with the choice window:

```python
# OLD:
relic_manager._open_shop()  # Sets shop_open flag

# NEW:
shop_window = create_relic_shop_window(game)
game.choice_window_manager.open_window(shop_window)
```

### 2. Add God Selection at Start

```python
# In game initialization:
god_window = create_god_selection_window(game)
game.choice_window_manager.open_window(god_window)
```

### 3. Create Sprite in Game

```python
# In Game sprite creation:
from farkle.ui.sprites.choice_window_sprite import ChoiceWindowSprite

# Create sprite when manager exists
if hasattr(self, 'choice_window_manager'):
    window = self.choice_window_manager.get_active_window()
    if window:
        ChoiceWindowSprite(window, self, self.renderer.sprite_groups['modal'])
```

## Benefits Over Old System

### Code Reusability
- **Before**: Separate `ShopOverlaySprite`, hypothetical `GodSelectionSprite`, etc.
- **After**: One `ChoiceWindowSprite` handles all selection screens

### Consistency
- **Before**: Each screen might look/behave differently
- **After**: All selection screens have same UI/UX

### Minimize Feature
- **Before**: Must decide without seeing current state
- **After**: Can minimize to inspect game before deciding

### Extensibility
- **Before**: Adding new selection screens requires new sprite classes
- **After**: Just create `ChoiceWindow` with items

### Testability
- **Before**: Testing requires full game setup
- **After**: Choice window can be tested in isolation

## Files Modified

- ✅ `farkle/core/game_event.py` - Added 7 new event types
- ✅ Created `farkle/ui/choice_window.py` - Core window logic
- ✅ Created `farkle/ui/choice_window_manager.py` - Lifecycle management
- ✅ Created `farkle/ui/sprites/choice_window_sprite.py` - Rendering
- ✅ Created `tests/test_choice_window.py` - Comprehensive tests
- ✅ Created `docs/CHOICE_WINDOW.md` - Documentation
- ✅ Created `examples/choice_window_demo.py` - Usage examples

## Test Results

```
252 passed, 4 skipped, 2 warnings in 5.75s
```

All existing tests still pass + 9 new choice window tests pass.

## Conclusion

The choice window system is **complete and ready to use**. It provides:

✅ General-purpose selection screens  
✅ Minimize/maximize for informed decisions  
✅ Single and multiple selection modes  
✅ Cost-based item availability  
✅ Event-driven architecture  
✅ Comprehensive tests  
✅ Full documentation  
✅ Practical examples  

The system can now be integrated into the game to replace the shop and add god selection at game start. The minimize/maximize feature is unique and enhances strategic gameplay by allowing players to inspect game state before making choices.
