from dataclasses import dataclass, field
from typing import List, Optional
from game_event import GameEvent, GameEventType
from relic import Relic
from score_modifiers import ScoreMultiplier

@dataclass
class RelicOffer:
    relic: Relic
    cost: int

class RelicManager:
    """Manages relic acquisition via a between-level shop.

    Flow:
    * On LEVEL_ADVANCE_FINISHED -> emit SHOP_OPENED + RELIC_OFFERED (single offer for now).
    * Input controller (or UI) will emit REQUEST_BUY_RELIC or REQUEST_SKIP_SHOP.
    * On REQUEST_BUY_RELIC (if enough gold) -> deduct gold, activate relic, RELIC_PURCHASED.
    * On REQUEST_SKIP_SHOP (or successful purchase) -> SHOP_CLOSED then start first turn of new level (TURN_START already emitted earlier) allowing play to resume.
    * During an open shop, gameplay requests (ROLL/LOCK/BANK) should be denied (handled externally by InputController/gating if needed).
    """

    def __init__(self, game):
        self.game = game
        self.active_relics: List[Relic] = []
        self.current_offer: Optional[RelicOffer] = None
        self.shop_open: bool = False

    # Event subscription entrypoint
    def on_event(self, event: GameEvent):  # type: ignore[override]
        et = event.type
        if et == GameEventType.LEVEL_ADVANCE_FINISHED:
            self._open_shop()
        elif et == GameEventType.REQUEST_BUY_RELIC and self.shop_open:
            self._attempt_purchase()
        elif et in (GameEventType.REQUEST_SKIP_SHOP,) and self.shop_open:
            self._close_shop(skipped=True)

    def _open_shop(self):
        # Generate a simple multiplier relic offer each level for now
        self.shop_open = True
        base_mult = 1.10  # +10% relic
        # Cheaper early-game: allow first relic purchase right after level 1.
        # Previous formula: 50 + 10*(level_index-1)
        # New formula: 20 + 5*(level_index-1) (Level 1 -> 20, Level 2 -> 25, etc.)
        cost = 20 + 5 * (self.game.level_index - 1)
        relic = Relic(name=f"Relic of Growth L{self.game.level_index}", base_multiplier=base_mult)
        self.current_offer = RelicOffer(relic=relic, cost=cost)
        el = self.game.event_listener
        el.publish(GameEvent(GameEventType.SHOP_OPENED, payload={
            "level_index": self.game.level_index
        }))
        el.publish(GameEvent(GameEventType.RELIC_OFFERED, payload={
            "name": relic.name,
            "multiplier": base_mult,
            "cost": cost
        }))

    def _attempt_purchase(self):
        if not self.current_offer:
            return
        offer = self.current_offer
        player = self.game.player
        if player.gold >= offer.cost:
            player.gold -= offer.cost
            self.active_relics.append(offer.relic)
            # Subscribe relic so it can (potentially) react to events later
            self.game.event_listener.subscribe(offer.relic.on_event)
            self.game.event_listener.publish(GameEvent(GameEventType.RELIC_PURCHASED, payload={
                "name": offer.relic.name,
                "cost": offer.cost,
                "multiplier": offer.relic.get_effective_multiplier()
            }))
            self._close_shop(skipped=False)
        else:
            self.game.event_listener.publish(GameEvent(GameEventType.MESSAGE, payload={
                "text": "Not enough gold for relic"
            }))

    def _close_shop(self, skipped: bool):
        self.game.event_listener.publish(GameEvent(GameEventType.SHOP_CLOSED, payload={
            "skipped": skipped
        }))
        self.current_offer = None
        self.shop_open = False

    def aggregate_modifier_chain(self):
        # Combine player base chain + all active relic chains into a temporary list
        mods = list(self.game.player.modifier_chain.snapshot())
        for r in self.active_relics:
            mods.extend(r.modifier_chain.snapshot())
        return mods
