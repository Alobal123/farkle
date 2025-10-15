import pygame, pytest
from game import Game
from level import Level
from game_event import GameEvent, GameEventType

def test_shop_overlay_receives_draw_calls(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((800,600))
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()
    g = Game(screen, font, clock, level=Level.single("L1", target_goal=10, max_turns=1, description=""))
    # Force advancement finished to open shop
    g.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={"level_index":1}))
    # Ensure shop_open flag set by relic manager
    assert g.relic_manager.shop_open, "Shop should be open after LEVEL_ADVANCE_FINISHED"
    # Locate ShopOverlay object
    from ui_objects import ShopOverlay
    shop_obj = next((o for o in g.ui_misc if isinstance(o, ShopOverlay)), None)
    assert shop_obj is not None, "ShopOverlay not present in ui_misc"
    # Monkeypatch its draw to record invocation
    called = {"count":0}
    orig_draw = shop_obj.draw
    def wrapped(surface):  # type: ignore
        called["count"] += 1
        return orig_draw(surface)
    monkeypatch.setattr(shop_obj, "draw", wrapped)
    # Execute one frame of run loop body manually (simulate run iteration)
    g.draw()
    assert called["count"] == 1, "Expected ShopOverlay.draw to be called during Game.draw()"
    # Basic sanity: purchase_rects generated after draw
    assert len(shop_obj.purchase_rects) > 0, "Expected purchase_rects populated after draw"
