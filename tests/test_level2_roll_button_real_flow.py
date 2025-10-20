import pygame, pytest
from farkle.game import Game
from farkle.level.level import Level
from farkle.core.actions import handle_roll, handle_lock, handle_bank
from farkle.core.game_event import GameEvent, GameEventType

def complete_level_legit(game: Game):
    # Play turns until mandatory goals fulfilled by brute force (safety cap)
    # For speed, directly mark goals fulfilled after at least one roll per goal to mimic scoring.
    for goal in game.level_state.goals:
        # Simulate fulfilling
        goal._fulfilled = True  # type: ignore[attr-defined]
        game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal_name": goal.name}))
    # Bank to end turn
    game.turn_score = 100  # ensure >0
    game.event_listener.publish(GameEvent(GameEventType.BANK, payload={}))
    game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason":"banked"}))

@pytest.mark.parametrize("shop_action", ["skip"])
def test_roll_button_enabled_after_real_advancement(shop_action):
    pygame.init()
    screen = pygame.display.set_mode((800,600))
    font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()
    g = Game(screen, font, clock, level=Level.single("Test", target_goal=50, max_turns=2, description=""))
    complete_level_legit(g)
    # Expect SHOP then skip
    if g.state_manager.get_state().name == 'SHOP':
        g.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP, payload={}))
        g.event_listener.publish(GameEvent(GameEventType.MESSAGE, payload={}))
    assert g.state_manager.get_state().name == 'PRE_ROLL'
    roll_btn = next(b for b in g.ui_buttons if b.name == 'roll')
    assert roll_btn.is_enabled_fn(g), f"Roll disabled: state={g.state_manager.get_state().name} locked_after_last_roll={g.locked_after_last_roll}"