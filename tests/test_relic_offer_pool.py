import pygame
import pytest
from farkle.game import Game
from farkle.relics.relic_manager import RelicManager
from farkle.relics.relic import Relic

@pytest.fixture
def game():
    try:
        pygame.init()
    except Exception:
        pass
    screen = pygame.Surface((800, 600))
    font = pygame.font.Font(None, 24)
    class DummyClock:
        def tick(self, fps):
            return 0
    return Game(screen, font, DummyClock())

def test_seeded_randomness_reproducible_order(game):
    # With a fixed seed we expect reproducible ordering across separate RelicManager instances.
    from farkle.core.game_event import GameEvent, GameEventType
    rm1 = RelicManager(game, randomize_offers=True, offer_seed=321)
    game.event_listener.publish(GameEvent(GameEventType.LEVEL_ADVANCE_FINISHED, payload={}))
    offers1 = [o.name for o in rm1._generate_offers()]
    # Recreate manager with same seed, generate again
    rm2 = RelicManager(game, randomize_offers=True, offer_seed=321)
    offers2 = [o.name for o in rm2._generate_offers()]
    assert offers1 == offers2 and offers1, "Seeded shuffle should be reproducible"

def test_filtering_excludes_owned(game):
    rm = RelicManager(game, randomize_offers=False)
    # Pretend we already own Charm of Fives
    owned = Relic(id="charm_of_fives", name="Charm of Fives", cost=0, description="")
    from farkle.scoring.score_modifiers import FlatRuleBonus
    owned.add_modifier(FlatRuleBonus(rule_key="SingleValue:5", amount=50))
    rm.active_relics.append(owned)
    offers = rm._generate_offers()
    names = [o.name for o in offers]
    assert "Charm of Fives" not in names, "Owned relic should not appear in offers"
    # Still produce up to 3 offers
    assert len(offers) <= 3
