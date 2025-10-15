import pygame
from game import Game
from level import Level
from game_event import GameEvent, GameEventType

# Helper to capture events
class Collector:
    def __init__(self):
        self.events = []
    def on_event(self, event: GameEvent):  # type: ignore
        self.events.append(event)

def simulate_completion_and_advance(game: Game):
    # Mark all goals fulfilled and end turn to trigger advancement
    for goal in game.level_state.goals:
        goal.remaining = 0  # mark fulfilled
        game.event_listener.publish(GameEvent(GameEventType.GOAL_FULFILLED, payload={"goal_name": goal.name}))
    # Bank to finish turn
    game.turn_score = 100
    game.event_listener.publish(GameEvent(GameEventType.BANK, payload={}))
    # Force TURN_END (normally emitted via SCORE_APPLIED cycle)
    game.event_listener.publish(GameEvent(GameEventType.TURN_END, payload={"reason":"banked"}))


def test_advancement_event_sequence_with_deferred_turn_start():
    pygame.init()
    screen = pygame.display.set_mode((800,600))
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()
    g = Game(screen, font, clock, level=Level.single("L1", target_goal=50, max_turns=1, description=""))
    collector = Collector()
    g.event_listener.subscribe(collector.on_event)
    simulate_completion_and_advance(g)
    # After advancement, shop should be open and TURN_START for new level not yet emitted
    names = [e.type for e in collector.events]
    # Find indices
    try:
        idx_finished = names.index(GameEventType.LEVEL_ADVANCE_FINISHED)
    except ValueError:
        raise AssertionError("LEVEL_ADVANCE_FINISHED not emitted")
    # Ensure SHOP_OPENED occurs after LEVEL_ADVANCE_FINISHED
    try:
        idx_shop_open = names.index(GameEventType.SHOP_OPENED)
    except ValueError:
        raise AssertionError("SHOP_OPENED not emitted")
    assert idx_shop_open > idx_finished, "SHOP_OPENED should occur after LEVEL_ADVANCE_FINISHED"
    # Ensure no TURN_START appears after LEVEL_ADVANCE_FINISHED yet (deferred)
    post_finished = names[idx_finished+1:]
    assert GameEventType.TURN_START not in post_finished, "TURN_START should be deferred until shop closes"
    # Skip shop
    g.event_listener.publish(GameEvent(GameEventType.REQUEST_SKIP_SHOP))
    # Now a TURN_START should occur after SHOP_CLOSED
    later = [e.type for e in collector.events[idx_shop_open+1:]]
    assert GameEventType.SHOP_CLOSED in later, "SHOP_CLOSED missing after skip"
    # TURN_START should appear after SHOP_CLOSED
    idx_closed = [i for i,t in enumerate(collector.events) if t.type == GameEventType.SHOP_CLOSED][-1]
    ts_after = [t.type for t in collector.events[idx_closed+1:]]
    assert GameEventType.TURN_START in ts_after, "TURN_START not emitted after shop close"
    # Final state should be PRE_ROLL
    assert g.state_manager.get_state().name == 'PRE_ROLL'
