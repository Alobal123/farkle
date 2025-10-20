from dataclasses import dataclass
from typing import List, Optional
import random
from farkle.core.game_event import GameEvent, GameEventType
from farkle.relics.relic import Relic
from farkle.scoring.score_modifiers import FlatRuleBonus

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
        self.current_offer: Optional[RelicOffer] = None  # single-offer reference (first offer convenience)
        self.offers: List[RelicOffer] = []  # multiple offers for new shop
        self.shop_open: bool = False

    # Event subscription entrypoint
    def on_event(self, event: GameEvent):  # type: ignore[override]
        et = event.type
        if et == GameEventType.LEVEL_ADVANCE_FINISHED:
            self._open_shop()
        elif et == GameEventType.REQUEST_BUY_RELIC and self.shop_open:
            # Optional index in payload selects which offer (default 0)
            idx = event.get("offer_index", 0)
            self._attempt_purchase(idx)
        elif et in (GameEventType.REQUEST_SKIP_SHOP,) and self.shop_open:
            self._close_shop(skipped=True)

    def _open_shop(self):
        self.shop_open = True
        el = self.game.event_listener
        self.offers = self._generate_offers()
        el.publish(GameEvent(GameEventType.SHOP_OPENED, payload={
            "level_index": self.game.level_index,
            "offers": [self._offer_payload(o) for o in self.offers]
        }))
        # Emit individual offer events (retain compatibility pattern)
        for idx, offer in enumerate(self.offers):
            payload = self._offer_payload(offer)
            payload["offer_index"] = idx
            el.publish(GameEvent(GameEventType.RELIC_OFFERED, payload=payload))
        # Set default current_offer to first (for older code paths)
        self.current_offer = self.offers[0] if self.offers else None

    def _generate_offers(self) -> List[RelicOffer]:
        """Return three random offers from a fixed relic pool each shop.

        Pool:
          * Flat +50 SingleValue:5
          * Flat +100 SingleValue:1
          * x1.5 multiplier to ALL ThreeOfAKind parts
          * x1.5 multiplier to ALL FourOfAKind parts
          * x1.5 multiplier to ALL Straights (full + partial)
        Costs chosen for rough balance; can be tweaked later.
        """
        from farkle.scoring.score_modifiers import RuleSpecificMultiplier
        from farkle.relics.relic import ExtraRerollRelic
        pool: List[RelicOffer] = []

        # Flat singles & ability-enhancing relics
        r5 = Relic(name="Charm of Fives")
        r5.add_modifier(FlatRuleBonus(rule_key="SingleValue:5", amount=50))
        charm_offer = RelicOffer(relic=r5, cost=30)  # deterministic cost expected by tests
        pool.append(charm_offer)

        r1 = Relic(name="Charm of Ones")
        r1.add_modifier(FlatRuleBonus(rule_key="SingleValue:1", amount=100))
        pool.append(RelicOffer(relic=r1, cost=45))

        extra_reroll = ExtraRerollRelic()
        pool.append(RelicOffer(relic=extra_reroll, cost=40))

        # Pattern multipliers
        m3 = Relic(name="Glyph of Triples")
        for v in range(1,7):
            m3.add_modifier(RuleSpecificMultiplier(rule_key=f"ThreeOfAKind:{v}", mult=1.5))
        pool.append(RelicOffer(relic=m3, cost=70))

        m4 = Relic(name="Sigil of Quadruples")
        for v in range(1,7):
            m4.add_modifier(RuleSpecificMultiplier(rule_key=f"FourOfAKind:{v}", mult=1.5))
        pool.append(RelicOffer(relic=m4, cost=65))

        ms = Relic(name="Runestone of Straights")
        for rk in ("Straight6", "Straight1to5", "Straight2to6"):
            ms.add_modifier(RuleSpecificMultiplier(rule_key=rk, mult=1.5))
        pool.append(RelicOffer(relic=ms, cost=60))

        random.shuffle(pool)
        level = getattr(self.game, 'level_index', 1)
        if level == 1:
            others = [o for o in pool if o.relic.name != "Charm of Fives"]
            random.shuffle(others)
            return [charm_offer] + others[:2]
        return pool[:3]

    def _offer_payload(self, offer: RelicOffer) -> dict:
        payload = {"name": offer.relic.name, "cost": offer.cost}
        # Detect flat bonuses
        from farkle.scoring.score_modifiers import FlatRuleBonus, CompositePartModifier
        for m in offer.relic.modifier_chain.snapshot():
            if isinstance(m, FlatRuleBonus):
                payload["flat_rule_bonus"] = {"rule_key": m.rule_key, "amount": m.amount}
        return payload

    def _attempt_purchase(self, index: int = 0):
        if not self.offers:
            return
        # Normalize index (handle None or non-int)
        try:
            if not isinstance(index, int):
                index = 0
        except Exception:
            index = 0
        try:
            if index < 0 or index >= len(self.offers):
                index = 0
        except Exception:
            index = 0
        offer = self.offers[index]
        player = self.game.player
        if player.gold >= offer.cost:
            reroll_before = None
            try:
                reroll_before = self.game.ability_manager.get('reroll').charges_per_level
            except Exception:
                pass
            player.gold -= offer.cost
            self.active_relics.append(offer.relic)
            # Activate relic (handles subscription bookkeeping). Relics start
            # active by default, but calling activate ensures future relics
            # that opt into deferred activation are wired consistently.
            try:
                # Force activation sequence even if relic.active True (set inactive then activate)
                offer.relic.active = False
                offer.relic.activate(self.game)
                # Explicit subscription safeguard (idempotent) to guarantee selective modifiers fire
                self.game.event_listener.subscribe(offer.relic.on_event)
            except Exception:
                # Fallback to legacy direct subscription if activate missing
                self.game.event_listener.subscribe(offer.relic.on_event)
            self.game.event_listener.publish(GameEvent(GameEventType.RELIC_PURCHASED, payload={
                "name": offer.relic.name,
                "offer_index": index,
                "cost": offer.cost,
            }))
            try:
                reroll_after = self.game.ability_manager.get('reroll').charges_per_level
            except Exception:
                reroll_after = None
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
        self.offers = []
        self.shop_open = False

    def active_relic_lines(self) -> list[str]:
        """Return human-readable lines describing currently active relics.

        Format per relic: Name (+flat bonuses, multipliers).
        Example: "Charm of Fives [+50 SingleValue:5]".
        """
        lines: list[str] = []
        if not self.active_relics:
            return ["Relics: (none)"]
        try:
            from farkle.scoring.score_modifiers import FlatRuleBonus, RuleSpecificMultiplier
        except Exception:
            FlatRuleBonus = RuleSpecificMultiplier = tuple()  # type: ignore
        for relic in self.active_relics:
            parts: list[str] = []
            try:
                for m in relic.modifier_chain.snapshot():
                    try:
                        from farkle.scoring.score_modifiers import FlatRuleBonus, RuleSpecificMultiplier
                        if isinstance(m, FlatRuleBonus):
                            parts.append(f"+{m.amount} {m.rule_key}")
                        elif isinstance(m, RuleSpecificMultiplier):
                            rk = getattr(m, 'rule_key', '')
                            parts.append(f"x{getattr(m,'mult',1.0):.2f} {rk}")
                    except Exception:
                        pass
            except Exception:
                pass
            # Ability modifications (+/- charges)
            try:
                for ability_id, delta in getattr(relic, 'ability_mods', []):
                    sign = '+' if delta > 0 else ''
                    unit = 'charge' if abs(delta) == 1 else 'charges'
                    parts.append(f"{sign}{delta} {ability_id} {unit}")
            except Exception:
                pass
            suffix = (" [" + ", ".join(parts) + "]") if parts else ""
            lines.append(f"{relic.name}{suffix}")
        return lines
