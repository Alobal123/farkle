from farkle.core.game_object import GameObject
from farkle.core.event_listener import EventListener
from farkle.core.game_event import GameEvent, GameEventType

class DummyGame:
    def __init__(self):
        self.event_listener = EventListener()
        self.state_manager = type('SM',(object,),{'get_state': lambda self: None})()

class HookObj(GameObject):
    def __init__(self):
        super().__init__("hook")
        self.active_calls = 0
        self.deactive_calls = 0
        self.events_seen = []
    def draw(self, surface):
        pass
    def on_activate(self, game):  # type: ignore[override]
        self.active_calls += 1
    def on_deactivate(self, game):  # type: ignore[override]
        self.deactive_calls += 1
    def on_event(self, event):  # type: ignore[override]
        if event.type == GameEventType.MESSAGE:
            self.events_seen.append(event.type)


def test_hooks_called_once_each():
    g = DummyGame()
    o = HookObj()
    # Start inactive to force first activate call
    o.active = False
    o.activate(g)
    assert o.active_calls == 1
    # Repeated activate should not increment
    o.activate(g)
    assert o.active_calls == 1
    # Emit event
    g.event_listener.publish(GameEvent(GameEventType.MESSAGE))
    assert o.events_seen == [GameEventType.MESSAGE]
    # Deactivate -> hook
    o.deactivate(g)
    assert o.deactive_calls == 1
    # Redundant deactivate
    o.deactivate(g)
    assert o.deactive_calls == 1
    # While inactive event not received
    g.event_listener.publish(GameEvent(GameEventType.MESSAGE))
    assert len(o.events_seen) == 1
