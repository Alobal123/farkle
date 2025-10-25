import pygame
import pytest
from farkle.game import Game
from farkle.level.level import Level
from farkle.core.game_event import GameEvent, GameEventType

def complete_level_via_events(game: Game):
    # Simulate fulfilling all mandatory goals by emitting GOAL_FULFILLED for each mandatory goal name.
    # This leverages existing game logic which marks completion when all mandatory fulfilled then waits for TURN_END.
    for idx in game.level_state.disaster_indices:
        goal = game.level_state.goals[idx]
        if not goal.is_fulfilled():
            # Manually mark goal fulfilled using its API if available; else set internal state and emit event
            try:
                goal._fulfilled = True  # type: ignore[attr-defined]
            except Exception:
                pass
            game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal_name": goal.name}))
    # Emit TURN_END with reason banked to trigger advance
    game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason": "banked"}))

@pytest.mark.parametrize("shop_action", ["skip"])  # future extension: purchase path
def test_roll_button_enabled_on_level2(shop_action):
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()
    g = Game(screen, font, clock, level=Level.single("Test", target_goal=50, max_turns=2, description=""))

    complete_level_via_events(g)

    # After advancement finishes, game may enter shop or go straight to PRE_ROLL depending on event ordering
    state_name = g.state_manager.get_state().name
    if state_name == 'SHOP':
        g.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP, payload={}))
        g.event_listener.publish(GameEvent(GameEventType.MESSAGE, payload={}))
        assert g.state_manager.get_state().name == 'PRE_ROLL'
    else:
        assert state_name == 'PRE_ROLL'
    roll_btn = next(b for b in g.ui_buttons if b.name == 'roll')
    assert roll_btn.is_enabled_fn(g), "Roll button should be enabled at start of level 2 PRE_ROLL"
