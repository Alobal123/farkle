# Choice Window System

A general-purpose modal window system for presenting choices to the player. This system can be used for god selection, relic shops, random events, or any other selection screen.

## Features

- **Minimize/Maximize**: Players can minimize the window to a corner icon to inspect the game state before making a decision
- **Single or Multiple Selection**: Configure min/max selections per window
- **Optional Skip**: Allow players to skip without selecting
- **Cost-Based Availability**: Items can be enabled/disabled based on cost or other criteria
- **Event-Driven**: All interactions emit events for clean integration with the game's event system

## Architecture

### Core Components

1. **`ChoiceWindow`** (`farkle/ui/choice_window.py`)
   - Manages window state (closed, maximized, minimized)
   - Handles item selection logic
   - Validates selections against min/max constraints

2. **`ChoiceItem`** (`farkle/ui/choice_window.py`)
   - Represents a single selectable option
   - Contains display information and selection callback
   - Supports optional cost and enabled state

3. **`ChoiceWindowManager`** (`farkle/ui/choice_window_manager.py`)
   - Manages window lifecycle (open/close)
   - Executes selection callbacks when window closes
   - Emits appropriate events

4. **`ChoiceWindowSprite`** (`farkle/ui/sprites/choice_window_sprite.py`)
   - Renders the window and its items
   - Handles minimize/maximize UI
   - Processes mouse clicks on buttons

## Usage Examples

### God Selection at Game Start

```python
from farkle.ui.choice_window import ChoiceWindow, ChoiceItem

def select_god(game, god_class):
    god = god_class(game=game)
    game.gods.worship(god)

items = [
    ChoiceItem(
        id="demeter",
        name="Demeter",
        description="Goddess of harvest and nature",
        payload=Demeter,
        on_select=select_god,
        effect_text="Level up through nature goals. +20% to nature scoring at level 1."
    ),
    # ... more gods
]

window = ChoiceWindow(
    title="Choose Your Patron God",
    items=items,
    window_type="god_selection",
    allow_skip=False,
    allow_minimize=True,
    min_selections=1,
    max_selections=2
)

game.choice_window_manager.open_window(window)
```

### Relic Shop

```python
def purchase_relic(game, relic):
    if game.player.gold >= relic.cost:
        game.player.gold -= relic.cost
        game.relic_manager.acquire_relic(relic)

items = []
for offer in shop_offers:
    items.append(ChoiceItem(
        id=offer.id,
        name=offer.name,
        description=offer.description,
        payload=offer.relic,
        on_select=purchase_relic,
        cost=offer.cost,
        enabled=game.player.gold >= offer.cost,
        effect_text=offer.effect_text
    ))

window = ChoiceWindow(
    title="Relic Shop",
    items=items,
    window_type="shop",
    allow_skip=True,
    allow_minimize=True,
    min_selections=0,
    max_selections=1
)

game.choice_window_manager.open_window(window)
```

### Random Event

```python
def apply_outcome(game, outcome):
    game.player.gold += outcome.get("gold_change", 0)
    # ... other effects

items = [
    ChoiceItem(
        id="option_a",
        name="Risky Choice",
        description="High risk, high reward",
        payload={"gold_change": 100, "curse": True},
        on_select=apply_outcome,
        effect_text="Gain 100 gold but receive a curse"
    ),
    ChoiceItem(
        id="option_b",
        name="Safe Choice",
        description="Play it safe",
        payload={"gold_change": 20},
        on_select=apply_outcome,
        effect_text="Gain 20 gold"
    )
]

window = ChoiceWindow(
    title="Mysterious Event",
    items=items,
    window_type="event",
    allow_skip=False,
    min_selections=1,
    max_selections=1
)

game.choice_window_manager.open_window(window)
```

## Event Flow

The choice window system emits events at key points:

1. **`CHOICE_WINDOW_OPENED`** - Window is displayed
   - Payload: `window_type`, `title`, `num_items`

2. **`CHOICE_WINDOW_MINIMIZED`** - Player minimizes window
   - Payload: `window_type`

3. **`CHOICE_WINDOW_MAXIMIZED`** - Player restores from minimized
   - Payload: `window_type`

4. **`CHOICE_ITEM_SELECTED`** - Player selects an item
   - Payload: `window_type`, `item_index`, `item_id`, `item_name`

5. **`REQUEST_CHOICE_CONFIRM`** - Player clicks confirm button
   - Triggers window closure and callback execution

6. **`REQUEST_CHOICE_SKIP`** - Player clicks skip button
   - Triggers window closure without executing callbacks

7. **`CHOICE_WINDOW_CLOSED`** - Window closes
   - Payload: `window_type`, `selected_count`, `selected_ids`, `skipped`

## Integration with Game

### Setup (in `Game.__init__`)

```python
from farkle.ui.choice_window_manager import ChoiceWindowManager

self.choice_window_manager = ChoiceWindowManager(self)
```

### Event Handling

```python
def on_event(self, event):
    if event.type == GameEventType.REQUEST_CHOICE_CONFIRM:
        self.choice_window_manager.close_window(event.get("window_type"))
    
    elif event.type == GameEventType.REQUEST_CHOICE_SKIP:
        self.choice_window_manager.skip_window(event.get("window_type"))
    
    elif event.type == GameEventType.CHOICE_WINDOW_CLOSED:
        # Handle post-closure logic based on window_type
        window_type = event.get("window_type")
        if window_type == "shop":
            self.begin_turn(from_shop=True)
```

### Sprite Creation (in `Game` initialization)

```python
from farkle.ui.sprites.choice_window_sprite import ChoiceWindowSprite

# Create sprite when choice window manager is initialized
# The sprite will automatically show/hide based on window state
if hasattr(self, 'choice_window_manager'):
    choice_window = self.choice_window_manager.get_active_window()
    if choice_window:
        sprite = ChoiceWindowSprite(choice_window, self, self.renderer.sprite_groups['modal'])
```

## Window States

A choice window can be in three states:

- **`CLOSED`** - Window is not visible
- **`MAXIMIZED`** - Window is fully visible and interactive
- **`MINIMIZED`** - Window is collapsed to a small icon in the corner

Players can freely toggle between MAXIMIZED and MINIMIZED to inspect the game state while keeping the window open.

## Selection Modes

### Single Selection (max_selections=1)

- Selecting a new item replaces the previous selection
- Used for: god selection, shop purchases

### Multiple Selection (max_selections>1)

- Multiple items can be selected up to the maximum
- Clicking a selected item deselects it
- Used for: choosing multiple gods, selecting multiple upgrades

## Design Rationale

### Why a General Choice Window?

The previous approach had separate systems for different selection screens (e.g., `ShopOverlaySprite`). This led to:

- Code duplication
- Inconsistent UI/UX
- Difficulty adding new selection screens

The general choice window provides:

- **Reusability**: One system handles all selection screens
- **Consistency**: All selection screens look and behave the same way
- **Minimization**: Unique feature allowing informed decisions
- **Extensibility**: Easy to add new selection screens

### Minimize/Maximize Feature

This is a key differentiator from the old shop system. Players can:

1. Open a selection screen (e.g., relic shop)
2. Minimize it to a corner icon
3. Inspect current game state (relics, goals, gold)
4. Maximize the window again
5. Make an informed decision

This prevents "blind" choices and enhances strategic gameplay.

## Migration from Old Shop System

To replace the old shop with the choice window:

1. Replace `ShopOverlaySprite` with `ChoiceWindowSprite`
2. Convert `ShopOffer` to `ChoiceItem`
3. Use `ChoiceWindowManager` instead of `relic_manager.shop_open` flag
4. Handle `REQUEST_CHOICE_CONFIRM` instead of `REQUEST_BUY_RELIC`
5. Handle `REQUEST_CHOICE_SKIP` instead of `REQUEST_SKIP_SHOP`

The choice window provides all the same functionality plus minimize/maximize.

## Testing

See `tests/test_choice_window.py` for comprehensive tests covering:

- Window state transitions
- Selection logic (single/multiple)
- Minimize/maximize behavior
- Manager integration
- Event emission

## Future Enhancements

Potential additions to the choice window system:

- **Icons**: Display icons for items (god symbols, relic images)
- **Preview**: Show detailed preview when hovering over items
- **Animation**: Smooth transitions when minimizing/maximizing
- **Keyboard Navigation**: Arrow keys + Enter to select
- **Tooltips**: Additional information on hover
- **Multi-page**: Paginate when there are many items
