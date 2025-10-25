from dataclasses import dataclass, field
from farkle.core.game_object import GameObject
from farkle.scoring.score_modifiers import ScoreModifierChain, ScoreModifier, FlatRuleBonus, RuleSpecificMultiplier, ConditionalScoreModifier, GlobalPartsMultiplier
from farkle.core.game_event import GameEventType

@dataclass
class Relic(GameObject):
    """Gameplay relic providing selective score modifiers.

    Each relic owns a modifier chain (part-level adjustments). Relics are
    normal GameObjects: activate() wires event subscription and emits
    SCORE_MODIFIER_ADDED events; centralized scoring applies modifiers.
    """
    active: bool = False
    modifier_chain: ScoreModifierChain = field(default_factory=ScoreModifierChain)
    # Ability modifications: list of (ability_id, delta) for UI description (non-authoritative; activation events drive logic)
    ability_mods: list[tuple[str,int]] = field(default_factory=list)
    id: str = ""
    name: str = ""
    cost: int = 0
    description: str = ""

    def __init__(self, id: str, name: str, cost: int, description: str, modifiers: list[ScoreModifier] | None = None, ability_mods: list[tuple[str, int]] | None = None):
        GameObject.__init__(self, name=name)
        self.active = False  # Relics start inactive; activate() is called after purchase
        self.id = id
        self.name = name
        self.cost = cost
        self.description = description
        self.modifier_chain = ScoreModifierChain()
        if modifiers:
            for modifier in modifiers:
                self.add_modifier(modifier)
        self.ability_mods = ability_mods or []

    def add_modifier(self, modifier: ScoreModifier):
        self.modifier_chain.add(modifier)

    # --- Internal helpers -------------------------------------------------
    def _collect_modifier_data(self, mod: ScoreModifier) -> dict:
        data = {}
        for k in ("rule_key", "mult", "amount", "priority"):
            if hasattr(mod, k):
                v = getattr(mod, k)
                if isinstance(v, (int, float, str)):
                    data[k] = v
        return data

    def _emit_all_modifier_events(self, game, event_type: GameEventType):
        """Emit an event per modifier (added or removed)."""
        try:
            from farkle.core.game_event import GameEvent
            for mod in self.modifier_chain.snapshot():
                try:
                    game.event_listener.publish_immediate(GameEvent(event_type, payload={
                        "relic": self.name,
                        "modifier_type": mod.__class__.__name__,
                        "priority": getattr(mod, 'priority', None),
                        "data": self._collect_modifier_data(mod),
                    }))
                except Exception:
                    pass
        except Exception:
            pass

    def on_activate(self, game):  # type: ignore[override]
        """Base activation: emit SCORE_MODIFIER_ADDED events for all modifiers."""
        self._emit_all_modifier_events(game, GameEventType.SCORE_MODIFIER_ADDED)

    def on_deactivate(self, game):  # type: ignore[override]
        """Base deactivation: emit SCORE_MODIFIER_REMOVED for all modifiers."""
        self._emit_all_modifier_events(game, GameEventType.SCORE_MODIFIER_REMOVED)

    def on_event(self, event):  # type: ignore[override]
        # No per-event score mutation; effects applied centrally.
        return

    def draw(self, surface):  # type: ignore[override]
        return  # Relics currently have no standalone sprite.


@dataclass
class ExtraRerollRelic(Relic):
    def __init__(self):
        super().__init__(
            id="extra_reroll",
            name="Token of Second Chance",
            cost=40,
            description="Start each turn with an extra reroll charge.",
            ability_mods=[("reroll", 1)]
        )

    def on_activate(self, game):  # type: ignore[override]
        # Emit ability-specific effect then defer to base for modifier events
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_CHARGES_ADDED, payload={
                "ability_id": "reroll",
                "delta": 1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_activate(game)

    def on_deactivate(self, game):  # type: ignore[override]
        """Remove the granted reroll charge while ensuring charges_per_level doesn't drop below charges_used."""
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_CHARGES_ADDED, payload={
                "ability_id": "reroll",
                "delta": -1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_deactivate(game)

@dataclass
class IncreaseMaxRerollRelic(Relic):
    def __init__(self):
        super().__init__(
            id="increase_max_reroll",
            name="Sigil of Duplication",
            cost=50,
            description="Allows rerolling up to 2 dice at once.",
            ability_mods=[("reroll", 1)]
        )

    def on_activate(self, game):  # type: ignore[override]
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_TARGETS_ADDED, payload={
                "ability_id": "reroll",
                "delta": 1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_activate(game)

    def on_deactivate(self, game):  # type: ignore[override]
        try:
            from farkle.core.game_event import GameEvent, GameEventType
            game.event_listener.publish_immediate(GameEvent(GameEventType.ABILITY_TARGETS_ADDED, payload={
                "ability_id": "reroll",
                "delta": -1,
                "source": self.name
            }))
        except Exception:
            pass
        super().on_deactivate(game)


@dataclass
class FarkleRescueRelic(Relic):
    def __init__(self):
        super().__init__(
            id="farkle_rescue",
            name="Farkle Rescue",
            cost=200,
            description="Once per turn, if you Farkle, you may reroll the dice that caused the Farkle."
        )

@dataclass
class FiveFlatBonusRelic(Relic):
    def __init__(self):
        super().__init__(
            id="five_flat_bonus",
            name="Five of a Kind Bonus",
            cost=150,
            description="Get a flat bonus of 500 points for scoring five of a kind.",
            modifiers=[
                FlatRuleBonus(rule_key="FiveOfAKind", amount=500)
            ]
        )

@dataclass
class SixFlatBonusRelic(Relic):
    def __init__(self):
        super().__init__(
            id="six_flat_bonus",
            name="Six of a Kind Bonus",
            cost=250,
            description="Get a flat bonus of 1000 points for scoring six of a kind.",
            modifiers=[
                FlatRuleBonus(rule_key="SixOfAKind", amount=1000)
            ]
        )

@dataclass
class TriplePairBonusRelic(Relic):
    def __init__(self):
        super().__init__(
            id="triple_pair_bonus",
            name="Triple Pair Bonus",
            cost=150,
            description="Get a flat bonus of 750 points for scoring three pairs.",
            modifiers=[
                FlatRuleBonus(rule_key="ThreePair", amount=750)
            ]
        )

@dataclass
class StraightBonusRelic(Relic):
    def __init__(self):
        super().__init__(
            id="straight_bonus",
            name="Straight Bonus",
            cost=200,
            description="Get a flat bonus of 1250 points for scoring a straight.",
            modifiers=[
                FlatRuleBonus(rule_key="Straight", amount=1250)
            ]
        )

@dataclass
class FullHouseBonusRelic(Relic):
    def __init__(self):
        super().__init__(
            id="full_house_bonus",
            name="Full House Bonus",
            cost=150,
            description="Get a flat bonus of 500 points for scoring a full house.",
            modifiers=[
                FlatRuleBonus(rule_key="FullHouse", amount=500)
            ]
        )

@dataclass
class TwoTripletsBonusRelic(Relic):
    def __init__(self):
        super().__init__(
            id="two_triplets_bonus",
            name="Two Triplets Bonus",
            cost=300,
            description="Get a flat bonus of 2000 points for scoring two triplets.",
            modifiers=[
                FlatRuleBonus(rule_key="TwoTriplets", amount=2000)
            ]
        )

@dataclass
class FourAndPairBonusRelic(Relic):
    def __init__(self):
        super().__init__(
            id="four_and_pair_bonus",
            name="Four and Pair Bonus",
            cost=250,
            description="Get a flat bonus of 1250 points for scoring four of a kind and a pair.",
            modifiers=[
                FlatRuleBonus(rule_key="FourOfAKindAndPair", amount=1250)
            ]
        )

@dataclass
class ThreeOfAKindValueIncreaseRelic(Relic):
    def __init__(self):
        super().__init__(
            id="three_of_a_kind_value_increase",
            name="Glyph of Triples",
            cost=70,
            description="Increase the value of three of a kind by 1.5x.",
            modifiers=[
                RuleSpecificMultiplier(rule_key="ThreeOfAKind", mult=1.5)
            ]
        )

@dataclass
class FourOfAKindValueIncreaseRelic(Relic):
    def __init__(self):
        super().__init__(
            id="four_of_a_kind_value_increase",
            name="Four of a Kind Value Increase",
            cost=200,
            description="Increase the value of four of a kind by 1.5x.",
            modifiers=[
                RuleSpecificMultiplier(rule_key="FourOfAKind", mult=1.5)
            ]
        )

@dataclass
class FiveOfAKindValueIncreaseRelic(Relic):
    def __init__(self):
        super().__init__(
            id="five_of_a_kind_value_increase",
            name="Five of a Kind Value Increase",
            cost=250,
            description="Increase the value of five of a kind by 1.5x.",
            modifiers=[
                RuleSpecificMultiplier(rule_key="FiveOfAKind", mult=1.5)
            ]
        )

@dataclass
class SixOfAKindValueIncreaseRelic(Relic):
    def __init__(self):
        super().__init__(
            id="six_of_a_kind_value_increase",
            name="Six of a Kind Value Increase",
            cost=300,
            description="Increase the value of six of a kind by 1.5x.",
            modifiers=[
                RuleSpecificMultiplier(rule_key="SixOfAKind", mult=1.5)
            ]
        )

def _is_disaster_goal(ctx):
    return getattr(ctx, 'goal', None) and getattr(ctx.goal, 'is_disaster', False)

@dataclass
class DisasterGoalScoreBonusRelic(Relic):
    def __init__(self):
        inner = GlobalPartsMultiplier(mult=1.2, description="Score +20% for disasters")
        super().__init__(
            id="disaster_goal_score_bonus",
            name="Talisman of Purpose",
            cost=65,
            description="Score +20% for disasters.",
            modifiers=[
                ConditionalScoreModifier(
                    predicate=_is_disaster_goal,
                    inner=inner
                )
            ]
        )

def _is_petition_goal(ctx):
    return getattr(ctx, 'goal', None) and not getattr(ctx.goal, 'is_disaster', False)

@dataclass
class PetitionGoalScoreBonusRelic(Relic):
    def __init__(self):
        inner = GlobalPartsMultiplier(mult=1.2, description="Score +20% for petitions")
        super().__init__(
            id="petition_goal_score_bonus",
            name="Charm of Opportunism",
            cost=55,
            description="Score +20% for petitions.",
            modifiers=[
                ConditionalScoreModifier(
                    predicate=_is_petition_goal,
                    inner=inner
                )
            ]
        )

@dataclass
class CharmOfFivesRelic(Relic):
    def __init__(self):
        super().__init__(
            id="charm_of_fives",
            name="Charm of Fives",
            cost=30,
            description="Get a flat bonus of 50 points for scoring with single 5s.",
            modifiers=[FlatRuleBonus(rule_key="SingleValue:5", amount=50)]
        )

@dataclass
class CharmOfOnesRelic(Relic):
    def __init__(self):
        super().__init__(
            id="charm_of_ones",
            name="Charm of Ones",
            cost=45,
            description="Get a flat bonus of 100 points for scoring with single 1s.",
            modifiers=[FlatRuleBonus(rule_key="SingleValue:1", amount=100)]
        )
