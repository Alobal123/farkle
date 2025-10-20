import unittest
from farkle.relics.relic import ExtraRerollRelic
from farkle.relics.relic_manager import RelicOffer
from farkle.core.game_event import GameEvent, GameEventType

class DummyGame:
    def __init__(self):
        from farkle.abilities.ability_manager import AbilityManager
        from farkle.core.game_event import GameEventType
        from farkle.core.event_listener import EventListener
        self.event_listener = EventListener()
        self.state_manager = type('S',(object,),{'get_state':lambda self2: type('St',(object,),{'name':'ROLLING'})()})()
        self.player = type('P',(object,),{'gold':100})()
        self.level_index = 1
        self.ability_manager = AbilityManager(self)
        # Wire ability manager events

    def set_message(self, msg):
        self.message = msg

class ExtraRerollRelicTests(unittest.TestCase):
    def test_purchase_grants_extra_reroll_charge(self):
        game = DummyGame()
        reroll = game.ability_manager.get('reroll')
        if reroll is None:
            self.fail("Reroll ability not registered")
        r = reroll
        base_available = r.available()
        # Activate relic directly (simulate purchase path)
        relic = ExtraRerollRelic()
        relic.active = False
        relic.activate(game)
        # After activation charges_per_level should have grown by 1
        self.assertEqual(r.charges_per_level, base_available + 1)
        # available() reflects new max - used (used unchanged)
        self.assertEqual(r.available(), base_available + 1)

if __name__ == '__main__':
    unittest.main()
