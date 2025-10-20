import unittest
from farkle.relics.relic import ExtraRerollRelic
from farkle.relics.relic_manager import RelicManager, RelicOffer

class DummyGame:
    def __init__(self):
        from farkle.abilities.ability_manager import AbilityManager
        from farkle.core.event_listener import EventListener
        self.event_listener = EventListener()
        self.state_manager = type('S',(object,),{'get_state':lambda self2: type('St',(object,),{'name':'ROLLING'})()})()
        self.player = type('P',(object,),{'gold':100})()
        self.level_index = 1
        self.ability_manager = AbilityManager(self)

class ExtraRerollRelicListingTests(unittest.TestCase):
    def test_listing_shows_reroll_charge(self):
        game = DummyGame()
        rm = RelicManager(game)
        relic = ExtraRerollRelic()
        relic.active = False
        relic.activate(game)
        rm.active_relics.append(relic)
        lines = rm.active_relic_lines()
        # Expect formatted ability mod
        joined = '\n'.join(lines)
        self.assertIn('+1 reroll charge', joined)

if __name__ == '__main__':
    unittest.main()
