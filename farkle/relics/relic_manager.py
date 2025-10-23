"""Relic shop management and offer generation."""

from dataclasses import dataclass
from typing import List, Optional, Callable
from farkle.core.game_event import GameEvent, GameEventType
from farkle.relics.relic import Relic


@dataclass
class RelicOffer:
    relic: Relic
    cost: int


class RelicManager:
    """Manages relic acquisition via a between-level shop.

    Flow:
    * LEVEL_ADVANCE_FINISHED -> open shop & emit offers.
    * REQUEST_BUY_RELIC -> purchase & activate.
    * REQUEST_SKIP_SHOP or purchase -> close shop.
    * Gameplay requests gated externally while shop_open.
    """

    def __init__(self, game, *, randomize_offers: bool = False, offer_seed: int | None = None):
        self.game = game
        self.active_relics: List[Relic] = []
        self.current_offer: Optional[RelicOffer] = None
        self.offers: List[RelicOffer] = []
        self.shop_open: bool = False
        self.randomize_offers = randomize_offers
        self.offer_seed = offer_seed

    # --- Event handling ---
    def on_event(self, event: GameEvent):  # type: ignore[override]
        et = event.type
        if et == GameEventType.LEVEL_ADVANCE_FINISHED:
            self._open_shop()
        elif et == GameEventType.REQUEST_BUY_RELIC and self.shop_open:
            idx = event.get("offer_index", 0)
            self._attempt_purchase(idx)
        elif et == GameEventType.REQUEST_SKIP_SHOP and self.shop_open:
            self._close_shop(skipped=True)

    # --- Offer pool configuration ---
    def _open_shop(self):
        self.shop_open = True
        self.offers = self._generate_offers()
        el = self.game.event_listener
        el.publish(GameEvent(GameEventType.SHOP_OPENED, payload={
            "level_index": self.game.level_index,
            "offers": [self._offer_payload(o) for o in self.offers]
        }))
        for idx, offer in enumerate(self.offers):
            payload = self._offer_payload(offer)
            payload["offer_index"] = idx
            el.publish(GameEvent(GameEventType.RELIC_OFFERED, payload=payload))
        self.current_offer = self.offers[0] if self.offers else None

    def _generate_offers(self) -> List[RelicOffer]:
        _build_pool_once()
        owned = {r.name for r in self.active_relics}
        entries: List[RelicOffer] = []
        for name, cost, builder in RELIC_OFFER_POOL:
            if name in owned:
                continue
            try:
                entries.append(RelicOffer(relic=builder(), cost=cost))
            except Exception:
                continue
        if self.randomize_offers and entries:
            rng = getattr(self.game, 'rng', None)
            if rng and self.offer_seed is not None:
                # Reseed temporarily for offer generation then restore original seed state
                original_state = rng.state()
                rng.reseed(self.offer_seed)
                rng.shuffle(entries)
                rng.set_state(original_state)
            elif rng:
                rng.shuffle(entries)
            else:
                import random
                if self.offer_seed is not None:
                    random.seed(self.offer_seed)
                random.shuffle(entries)
        # Ensure deterministic first offer for tests if present.
        # No forced ordering; pure shuffle or original iteration filtering only.
        return entries[:3]

    def _offer_payload(self, offer: RelicOffer) -> dict:
        payload = {"name": offer.relic.name, "cost": offer.cost}
        from farkle.scoring.score_modifiers import FlatRuleBonus
        for m in offer.relic.modifier_chain.snapshot():
            if isinstance(m, FlatRuleBonus):
                payload["flat_rule_bonus"] = {"rule_key": m.rule_key, "amount": m.amount}
        return payload

    # --- Purchase flow ---
    def _attempt_purchase(self, index: int = 0):
        if not self.offers:
            return
        if not isinstance(index, int) or index < 0 or index >= len(self.offers):
            index = 0
        offer = self.offers[index]
        player = self.game.player
        if player.gold < offer.cost:
            self.game.event_listener.publish(GameEvent(GameEventType.MESSAGE, payload={"text": "Not enough gold for relic"}))
            return
        player.gold -= offer.cost
        self.active_relics.append(offer.relic)
        try:
            offer.relic.active = False
            offer.relic.activate(self.game)
            self.game.event_listener.subscribe(offer.relic.on_event)
        except Exception:
            self.game.event_listener.subscribe(offer.relic.on_event)
        self.game.event_listener.publish(GameEvent(GameEventType.RELIC_PURCHASED, payload={
            "name": offer.relic.name,
            "offer_index": index,
            "cost": offer.cost,
        }))
        self._close_shop(skipped=False)

    def _close_shop(self, skipped: bool):
        self.game.event_listener.publish(GameEvent(GameEventType.SHOP_CLOSED, payload={"skipped": skipped}))
        self.current_offer = None
        self.offers = []
        self.shop_open = False

    # --- Debug/UI helpers ---
    def active_relic_lines(self) -> list[str]:
        if not self.active_relics:
            return ["Relics: (none)"]
        try:
            from farkle.scoring.score_modifiers import FlatRuleBonus, RuleSpecificMultiplier
        except Exception:
            FlatRuleBonus = RuleSpecificMultiplier = tuple()  # type: ignore
        lines: list[str] = []
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


# --- Global offer pool configuration & builder helpers ---
RELIC_OFFER_POOL: List[tuple[str, int, Callable[[], Relic]]] = []


def _build_pool_once():
    from farkle.relics.relic import ExtraRerollRelic, MultiRerollRelic, MandatoryFocusTalisman, OptionalFocusCharm
    if RELIC_OFFER_POOL:
        return
    RELIC_OFFER_POOL.extend([
        ("Charm of Fives", 30, lambda: _flat_relic("Charm of Fives", "SingleValue:5", 50)),
        ("Charm of Ones", 45, lambda: _flat_relic("Charm of Ones", "SingleValue:1", 100)),
        ("Token of Second Chance", 40, lambda: ExtraRerollRelic()),
        ("Glyph of Triples", 70, lambda: _triples_relic()),
        ("Sigil of Duplication", 50, lambda: MultiRerollRelic()),
        ("Talisman of Purpose", 65, lambda: MandatoryFocusTalisman()),
        ("Charm of Opportunism", 55, lambda: OptionalFocusCharm()),
    ])


def _flat_relic(name: str, rule_key: str, amount: int) -> Relic:
    r = Relic(name=name)
    from farkle.scoring.score_modifiers import FlatRuleBonus
    r.add_modifier(FlatRuleBonus(rule_key=rule_key, amount=amount))
    return r


def _triples_relic() -> Relic:
    r = Relic(name="Glyph of Triples")
    from farkle.scoring.score_modifiers import RuleSpecificMultiplier
    for v in range(1, 7):
        r.add_modifier(RuleSpecificMultiplier(rule_key=f"ThreeOfAKind:{v}", mult=1.5))
    return r
