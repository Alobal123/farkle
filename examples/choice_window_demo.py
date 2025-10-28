"""
Demonstration of the Choice Window System

This shows how to use the general choice window for:
1. God selection at game start
2. Relic shop between levels
3. Any custom selection screens

The choice window can be minimized to inspect game state before deciding.
"""

from farkle.ui.choice_window import ChoiceWindow, ChoiceItem
from farkle.ui.choice_window_manager import ChoiceWindowManager


# Example 1: God Selection at Game Start
def create_god_selection_window(game):
    """Create a choice window for selecting starting gods."""
    
    def select_god(game, god_class):
        """Called when a god is selected."""
        god = god_class(game=game)
        game.gods.worship(god)
        print(f"Selected god: {god.name}")
    
    # Import god classes
    from farkle.gods.demeter import Demeter
    from farkle.gods.ares import Ares
    from farkle.gods.hades import Hades
    from farkle.gods.hermes import Hermes
    
    items = [
        ChoiceItem(
            id="demeter",
            name="Demeter",
            description="Goddess of harvest, growth, and natural abundance",
            payload=Demeter,
            on_select=select_god,
            effect_text="Level up through nature goals. Gain +20% to nature scoring at level 1."
        ),
        ChoiceItem(
            id="ares",
            name="Ares",
            description="God of war, conflict, and martial prowess",
            payload=Ares,
            on_select=select_god,
            effect_text="Level up through warfare goals. Gain +20% to warfare scoring at level 1."
        ),
        ChoiceItem(
            id="hades",
            name="Hades",
            description="God of the underworld and the dead",
            payload=Hades,
            on_select=select_god,
            effect_text="Level up through spirit goals. Gain +20% to spirit scoring at level 1."
        ),
        ChoiceItem(
            id="hermes",
            name="Hermes",
            description="God of commerce, travel, and cunning",
            payload=Hermes,
            on_select=select_god,
            effect_text="Level up through commerce goals. Gain +20% to commerce scoring at level 1."
        )
    ]
    
    window = ChoiceWindow(
        title="Choose Your Patron God",
        items=items,
        window_type="god_selection",
        allow_skip=False,  # Must select a god
        allow_minimize=True,  # Can minimize to see game info
        min_selections=1,
        max_selections=2  # Can worship up to 2 gods
    )
    
    return window


# Example 2: Relic Shop (Replacement for current shop)
def create_relic_shop_window(game):
    """Create a choice window for the relic shop."""
    
    def purchase_relic(game, relic):
        """Called when a relic is purchased."""
        if game.player.gold >= relic.cost:
            game.player.gold -= relic.cost
            game.relic_manager.acquire_relic(relic)
            print(f"Purchased: {relic.name} for {relic.cost}g")
    
    # Generate relic offers (using existing relic manager logic)
    offers = game.relic_manager._generate_offers()
    
    items = []
    for offer in offers:
        relic = offer.payload
        can_afford = game.player.gold >= offer.cost
        
        items.append(ChoiceItem(
            id=offer.id,
            name=offer.name,
            description=relic.description if hasattr(relic, 'description') else "",
            payload=relic,
            on_select=purchase_relic,
            cost=offer.cost,
            enabled=can_afford,
            effect_text=offer.effect_text
        ))
    
    window = ChoiceWindow(
        title="Relic Shop",
        items=items,
        window_type="shop",
        allow_skip=True,  # Can skip shop
        allow_minimize=True,  # Can minimize to check current relics/gold
        min_selections=0,  # Can buy 0 relics
        max_selections=1  # Can only buy 1 relic per shop visit
    )
    
    return window


# Example 3: Custom Event Selection (like Slay the Spire events)
def create_event_choice_window(game, event_data):
    """Create a choice window for a random event."""
    
    def apply_event_outcome(game, outcome):
        """Called when an event choice is made."""
        if "gold_change" in outcome:
            game.player.gold += outcome["gold_change"]
        if "message" in outcome:
            print(outcome["message"])
    
    # Example event: "Mysterious Shrine"
    items = [
        ChoiceItem(
            id="pray",
            name="Pray at the Shrine",
            description="Offer your prayers to the unknown deity.",
            payload={"gold_change": -50, "blessing": "random", "message": "The deity smiles upon you."},
            on_select=apply_event_outcome,
            cost=50,
            enabled=game.player.gold >= 50,
            effect_text="Pay 50 gold to receive a random blessing."
        ),
        ChoiceItem(
            id="loot",
            name="Loot the Shrine",
            description="Take what treasures you can find.",
            payload={"gold_change": 100, "curse": True, "message": "You anger the deity!"},
            on_select=apply_event_outcome,
            effect_text="Gain 100 gold but receive a curse."
        ),
        ChoiceItem(
            id="leave",
            name="Leave Quietly",
            description="Best not to tempt fate.",
            payload={"message": "You walk away unharmed."},
            on_select=apply_event_outcome,
            effect_text="No effect."
        )
    ]
    
    window = ChoiceWindow(
        title="Mysterious Shrine",
        items=items,
        window_type="event",
        allow_skip=False,  # Must make a choice
        allow_minimize=True,  # Can minimize to check resources
        min_selections=1,
        max_selections=1
    )
    
    return window


# How to use the choice window in game:

def example_usage(game):
    """Example of how to integrate choice windows into the game."""
    
    # Create the manager (usually done in game initialization)
    manager = ChoiceWindowManager(game)
    game.choice_window_manager = manager
    
    # Example 1: God selection at game start
    god_window = create_god_selection_window(game)
    manager.open_window(god_window)
    # Window is now open and can be interacted with
    # Player can minimize it to see the starting game state
    # When they confirm their selection, on_select is called for each selected god
    
    # Example 2: Relic shop after level
    # (This would replace the current shop system)
    shop_window = create_relic_shop_window(game)
    manager.open_window(shop_window)
    # Window shows relics, player can minimize to check current state
    # When they purchase or skip, the window closes
    
    # Example 3: Random event
    event_window = create_event_choice_window(game, event_data={})
    manager.open_window(event_window)
    # Player makes a choice, outcome is applied


# Event handling in the game loop:

def handle_choice_window_events(game, event):
    """Handle choice window events (add to game's event listener)."""
    from farkle.core.game_event import GameEventType
    
    if event.type == GameEventType.REQUEST_CHOICE_CONFIRM:
        window_type = event.get("window_type")
        game.choice_window_manager.close_window(window_type)
    
    elif event.type == GameEventType.REQUEST_CHOICE_SKIP:
        window_type = event.get("window_type")
        game.choice_window_manager.skip_window(window_type)
    
    elif event.type == GameEventType.CHOICE_WINDOW_CLOSED:
        window_type = event.get("window_type")
        skipped = event.get("skipped", False)
        
        if window_type == "shop" and not skipped:
            # After shop closes, continue to next turn
            game.begin_turn(from_shop=True)
        elif window_type == "god_selection":
            # After god selection, start the game
            game.begin_turn(initial=True)


if __name__ == "__main__":
    print("Choice Window System Demo")
    print("=" * 50)
    print()
    print("The choice window system provides:")
    print("- Minimize/maximize to inspect game state")
    print("- Single or multiple selection modes")
    print("- Optional skip button")
    print("- Cost-based item availability")
    print("- Event-driven selection handling")
    print()
    print("Use cases:")
    print("1. God selection at game start")
    print("2. Relic shop between levels")
    print("3. Random events with choices")
    print("4. Any future selection screens")
