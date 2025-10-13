import random
from typing import List
from die import Die
from game_event import GameEvent, GameEventType
from settings import HEIGHT, DICE_SIZE, MARGIN


class DiceContainer:
    """Encapsulates dice lifecycle & selection logic."""

    def __init__(self, game, count: int = 6):
        self.game = game
        self.dice: List[Die] = []
        self.count = count
        self.reset_all()

    # --- lifecycle -------------------------------------------------
    def reset_all(self):
        self.dice = [
            Die(
                random.randint(1, 6),
                100 + i * (DICE_SIZE + MARGIN),
                HEIGHT // 2 - DICE_SIZE // 2,
            )
            for i in range(self.count)
        ]

    def roll(self):
        el = self.game.event_listener
        el.publish(GameEvent(GameEventType.PRE_ROLL, payload={}))
        raw_values: list[int] = []
        for idx, d in enumerate(self.dice):
            if not d.held:
                old = d.value
                d.value = random.randint(1, 6)
                d.selected = False
                raw_values.append(d.value)
                el.publish(GameEvent(GameEventType.DIE_ROLLED, payload={"index": idx, "old": old, "new": d.value}))
            else:
                raw_values.append(d.value)
        self.game.locked_after_last_roll = False
        el.publish(GameEvent(GameEventType.POST_ROLL, payload={"values": list(raw_values)}))

    def mark_scoring(self):
        for d in self.dice:
            d.scoring_eligible = False
        unheld = [d for d in self.dice if not d.held]
        if not unheld:
            return
        values = [int(d.value) for d in unheld]
        _, contributing, _ = self.game.rules.evaluate(values)
        for i in contributing:
            unheld[i].scoring_eligible = True

    # --- queries ---------------------------------------------------
    def any_scoring_selection(self) -> bool:
        return any(d.selected and d.scoring_eligible for d in self.dice)

    def selection_values(self) -> list[int]:
        return [int(d.value) for d in self.dice if d.selected]

    def all_held(self) -> bool:
        return all(d.held for d in self.dice)

    def unheld_values(self) -> list[int]:
        return [int(d.value) for d in self.dice if not d.held]

    def check_farkle(self) -> bool:
        unheld = [d for d in self.dice if not d.held]
        if not unheld:
            return False
        values = [int(d.value) for d in unheld]
        score, _, _ = self.game.rules.evaluate(values)
        return score == 0

    # --- mutations -------------------------------------------------
    def hold_selected_publish(self):
        for d in self.dice:
            if d.selected:
                d.hold()
                self.game.event_listener.publish(GameEvent(GameEventType.DIE_HELD, payload={"index": self.dice.index(d), "value": d.value}))

    # --- scoring helpers -------------------------------------------
    def calculate_selected_score(self):
        values = self.selection_values()
        if not values:
            return 0, []
        total, indices, _ = self.game.rules.evaluate(values)
        return total, indices

    def selection_is_single_combo(self) -> bool:
        selected_values = self.selection_values()
        if not selected_values:
            return False
        matches = self.game.rules.evaluate_matches(selected_values)
        if not matches:
            return False
        full_cover = [m for m in matches if len(m[2]) == len(selected_values)]
        if not full_cover:
            return False
        max_size = max(m[0].combo_size for m in full_cover if hasattr(m[0], "combo_size"))
        best = [m for m in full_cover if getattr(m[0], "combo_size", 0) == max_size]
        return len(best) == 1 and best[0][0].combo_size == len(selected_values)

    def selection_rule_key(self) -> str | None:
        selected_values = self.selection_values()
        if not selected_values:
            return None
        matches = self.game.rules.evaluate_matches(selected_values)
        if not matches:
            return None
        full_cover = [m for m in matches if len(m[2]) == len(selected_values)]
        if not full_cover:
            return None
        max_size = max(m[0].combo_size for m in full_cover if hasattr(m[0], "combo_size"))
        best = [m for m in full_cover if getattr(m[0], "combo_size", 0) == max_size]
        if len(best) == 1 and best[0][0].combo_size == len(selected_values):
            rule = best[0][0]
            return getattr(rule, 'rule_key', rule.__class__.__name__)
        return None
