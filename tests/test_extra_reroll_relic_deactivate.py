import unittest
from farkle.relics.relic import ExtraRerollRelic

class DummyGame:
    def __init__(self):
        from farkle.abilities.ability_manager import AbilityManager
        from farkle.core.event_listener import EventListener
        self.event_listener = EventListener()
        self.state_manager = type('S',(object,),{'get_state':lambda self2: type('St',(object,),{'name':'ROLLING'})()})()
        self.player = type('P',(object,),{'gold':100})()
        self.level_index = 1
        self.ability_manager = AbilityManager(self)

class ExtraRerollRelicDeactivateTests(unittest.TestCase):
    def test_deactivate_removes_charge_without_going_negative(self):
        game = DummyGame()
        reroll = game.ability_manager.get('reroll')
        if reroll is None:
            self.fail("Reroll ability missing")
        r = reroll
        base = r.charges_per_level
        relic = ExtraRerollRelic()
        relic.active = False
        relic.activate(game)
        self.assertEqual(r.charges_per_level, base + 1)
        # Use one charge so used=1 then deactivate (capacity should not drop below used)
        r.consume()
        self.assertEqual(r.charges_used, 1)
        relic.deactivate(game)
        self.assertEqual(r.charges_per_level, max(base, r.charges_used))
        # Deactivating again should not change
        relic.deactivate(game)
        self.assertEqual(r.charges_per_level, max(base, r.charges_used))

if __name__ == '__main__':
    unittest.main()
