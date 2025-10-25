from dataclasses import dataclass, field
from typing import Any, Callable, Optional

@dataclass
class ShopOffer:
    """
    A generic container for an item offered in the shop.
    This is decoupled from any specific item type like Relic.
    """
    id: str
    name: str
    cost: int
    payload: Any  # The actual item, e.g., a Relic object
    on_purchase: Callable[[Any, Any], None] # A function to call when purchased (game, payload) -> None
    effect_text: Optional[str] = field(default=None)

    def __init__(self, id: str, name: str, cost: int, payload: Any, on_purchase: Callable, effect_text: Optional[str] = None):
        self.id = id
        self.name = name
        self.cost = cost
        self.payload = payload
        self.on_purchase = on_purchase
        self.effect_text = effect_text
