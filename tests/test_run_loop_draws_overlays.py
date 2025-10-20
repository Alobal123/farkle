import pygame, pytest
from farkle.game import Game
from farkle.level.level import Level
from farkle.core.game_event import GameEvent, GameEventType


def test_shop_state_populates_offers_without_dedicated_screen():
    """After level advancement finishes, the integrated shop state should populate relic offers.

    The dedicated ShopScreen was removed; validation now asserts:
    * shop_open flag set
    * offers list populated
    * drawing a normal frame does not error while shop is open
    """
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()
    g = Game(screen, font, clock, level=Level.single("L1", target_goal=10, max_turns=1, description=""))
    # Force advancement finished to open shop
    g.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index": 1}))
    assert g.relic_manager.shop_open, "Shop should be open after LEVEL_ADVANCE_FINISHED"
    # Run one frame of the standard game loop draw while in shop state
    g.draw()
    pygame.display.flip()
    # Ensure offers exist (single offer for now)
    assert getattr(g.relic_manager, 'offers', []), "Expected offers populated in relic_manager"
