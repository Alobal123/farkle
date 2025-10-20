import pytest
from farkle.core.game_event import GameEvent, GameEventType
from farkle.core.game_object import GameObject
from farkle.core.event_listener import EventListener

class Dummy(GameObject):
    def __init__(self, name="dummy", auto_active=True):
        super().__init__(name)
        self.active = auto_active
        self.events = []
    def draw(self, surface):
        pass
    def on_event(self, event):  # type: ignore[override]
        self.events.append(event.type)

class DummyGame:
    def __init__(self):
        self.event_listener = EventListener()
        self.state_manager = type('X',(object,),{'get_state': lambda self: None})()

def test_activation_and_emission():
    game = DummyGame()
    d = Dummy(auto_active=False)
    # Initially not subscribed
    game.event_listener.publish(GameEvent(GameEventType.MESSAGE))
    assert d.events == []
    # Activate (subscribe) and emit custom event through helper
    d.activate(game)
    d.emit(game, GameEventType.MESSAGE, {"text": "hi"})
    assert GameEventType.MESSAGE in d.events
    # Deactivate and ensure no further accumulation
    d.deactivate(game)
    game.event_listener.publish(GameEvent(GameEventType.MESSAGE))
    assert len(d.events) == 1


def test_activate_with_extra_callback():
    game = DummyGame()
    d = Dummy(auto_active=False)
    extra = []
    def cb(ev):
        extra.append(ev.type)
    d.activate(game, callback=cb)
    game.event_listener.publish(GameEvent(GameEventType.MESSAGE))
    assert GameEventType.MESSAGE in d.events
    assert GameEventType.MESSAGE in extra
    d.deactivate(game)
    game.event_listener.publish(GameEvent(GameEventType.MESSAGE))
    # No new events captured after deactivation
    assert len(extra) == 1
