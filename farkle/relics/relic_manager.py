"""Relic shop management and offer generation."""

from dataclasses import dataclass
from typing import List, Optional, Callable
from farkle.core.game_event import GameEvent, GameEventType
from farkle.relics.relic import Relic
from farkle.shop.offer import ShopOffer


class RelicManager:
    """Manages relic acquisition via a between-level shop.

    Flow:
    * LEVEL_ADVANCE_FINISHED -> open shop & emit offers.
    * REQUEST_BUY_RELIC -> purchase & activate.
    * REQUEST_SKIP_SHOP or purchase -> close shop.
    * Gameplay requests gated externally while shop_open.
    """

    def __init__(self, game, *, randomize_offers: bool = True, offer_seed: int | None = None):
        self.game = game
        self.active_relics: List[Relic] = []
        self.offers: List[ShopOffer] = []
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

    def _generate_offers(self) -> List[ShopOffer]:
        _build_pool_once()
        owned = {r.name for r in self.active_relics}
        entries: List[ShopOffer] = []
        for relic_class in RELIC_OFFER_POOL:
            try:
                relic = relic_class()
                if relic.name in owned:
                    continue
                offer = ShopOffer(
                    id=relic.uid,
                    name=relic.name,
                    cost=relic.cost,
                    payload=relic,
                    on_purchase=self._purchase_relic,
                    effect_text=self._get_relic_effect_text(relic)
                )
                entries.append(offer)
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
        return entries[:3]

    def _get_relic_description(self, relic: Relic) -> str:
        return relic.description

    def _get_relic_effect_text(self, relic: Relic) -> str:
        from farkle.scoring.score_modifiers import FlatRuleBonus, RuleSpecificMultiplier, ConditionalScoreModifier, GlobalPartsMultiplier
        
        def _format_rule_key(key: str) -> str:
            if not key: return "scores"
            
            if key.startswith("SingleValue:"):
                return f"scores with single {key.split(':')[1]}s"
            if key.startswith("ThreeOfAKind:"):
                return f"three {key.split(':')[1]}s"
            if key.startswith("FourOfAKind:"):
                return f"four {key.split(':')[1]}s"
            if key.startswith("FiveOfAKind:"):
                return f"five {key.split(':')[1]}s"
            if key.startswith("SixOfAKind:"):
                return f"six {key.split(':')[1]}s"
            if key == "Straight6":
                return "a 6-dice straight"
            if key == "Straight1to5":
                return "a 1-5 straight"
            if key == "Straight2to6":
                return "a 2-6 straight"
            return key # Fallback

        parts = []
        if relic.name == "Glyph of Triples":
            parts.append("Multiplies all 'Three of a Kind' scores by x1.5.")
        else:
            for m in relic.modifier_chain.snapshot():
                if isinstance(m, FlatRuleBonus):
                    rule_name = _format_rule_key(m.rule_key)
                    parts.append(f"Grants +{m.amount} points to {rule_name}.")
                elif isinstance(m, RuleSpecificMultiplier):
                    rule_name = _format_rule_key(m.rule_key)
                    parts.append(f"Multiplies {rule_name} scores by x{m.mult:.1f}.")
                elif isinstance(m, ConditionalScoreModifier) and hasattr(m, 'inner'):
                    inner_mod = m.inner
                    if isinstance(inner_mod, GlobalPartsMultiplier) and hasattr(inner_mod, 'description'):
                        parts.append(inner_mod.description)

        for ability_id, delta in getattr(relic, 'ability_mods', []):
            if relic.name == "Sigil of Duplication":
                parts.append("Allows rerolling up to 2 dice at once.")
            else:
                plural = "charge" if abs(delta) == 1 else "charges"
                parts.append(f"Grants {delta} {ability_id} {plural}.")
        return " ".join(parts) if parts else "Its purpose is a mystery."

    def _offer_payload(self, offer: ShopOffer) -> dict:
        relic = offer.payload
        return {"name": offer.name, "cost": offer.cost, "description": relic.description}

    # --- Purchase flow ---
    def _attempt_purchase(self, index: int = 0):
        if not self.offers:
            return
        if not isinstance(index, int) or index < 0 or index >= len(self.offers):
            index = 0
        offer = self.offers[index]
        player = self.game.player
        if player.gold < offer.cost:
            self.game.event_listener.publish(GameEvent(GameEventType.MESSAGE, payload={"text": "Not enough gold"}))
            return
        
        player.gold -= offer.cost
        offer.on_purchase(self.game, offer.payload)

        self.game.event_listener.publish(GameEvent(GameEventType.RELIC_PURCHASED, payload={
            "name": offer.name,
            "offer_index": index,
            "cost": offer.cost,
        }))
        self._close_shop(skipped=False)

    def _purchase_relic(self, game, relic: Relic):
        self.active_relics.append(relic)
        relic.activate(game)
        game.event_listener.subscribe(relic.on_event)

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
RELIC_OFFER_POOL: List[type[Relic]] = []


def _build_pool_once():
    from farkle.relics.relic import (
        ExtraRerollRelic, IncreaseMaxRerollRelic, DisasterGoalScoreBonusRelic, 
        PetitionGoalScoreBonusRelic, ThreeOfAKindValueIncreaseRelic,
        CharmOfFivesRelic, CharmOfOnesRelic
    )
    if RELIC_OFFER_POOL:
        return
    RELIC_OFFER_POOL.extend([
        CharmOfFivesRelic,
        CharmOfOnesRelic,
        ExtraRerollRelic,
        ThreeOfAKindValueIncreaseRelic,
        IncreaseMaxRerollRelic,
        DisasterGoalScoreBonusRelic,
        PetitionGoalScoreBonusRelic,
    ])
