import pygame
import pytest
from farkle.core.game_event import GameEvent, GameEventType
from farkle import Game  # updated to packaged Game implementation
from farkle.level.level import Level

@pytest.mark.parametrize("delta", [1])
def test_reroll_charge_event_increments(delta):
    pygame.init()
    screen = pygame.display.set_mode((1,1))
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()
    g = Game(screen, font, clock, level=Level.single('Dbg', target_goal=10, max_turns=1, description=''))
    reroll = g.ability_manager.get('reroll')
    assert reroll is not None
    before = reroll.charges_per_level
    # Publish ability charge event
    g.event_listener.publish(GameEvent(GameEventType.ABILITY_CHARGES_ADDED, payload={
        'ability_id': 'reroll',
        'delta': delta,
        'source': 'test'
    }))
    after = reroll.charges_per_level
    assert after == before + delta, f"Expected +{delta} charge (before={before} after={after})"
