import random
from typing import List
from die import Die
from game_event import GameEvent, GameEventType
from settings import HEIGHT, DICE_SIZE, MARGIN


class DiceContainer:
    """Encapsulates the game's dice and related operations.

    Responsibilities
    ---------------
    - Maintain authoritative list of Die objects for a Game instance.
    - Perform lifecycle operations: reset, roll, mark scoring eligibility, hold selected dice.
    - Provide query helpers (selection values, scoring checks, farkle detection, etc.).
    - Emit dice lifecycle events so tests/UI/analytics can observe state changes deterministically.

    Event Guarantees
    ----------------
    roll():
        1. Emit PRE_ROLL exactly once per invocation before mutating any die.
        2. For each non-held die emit DIE_ROLLED after assigning its new value & clearing selection.
        3. Always emit POST_ROLL with list of final face values (including held dice) in index order.
        locked_after_last_roll on the owning Game is cleared even if no dice changed.

    hold_selected_publish():
        - Emits one DIE_HELD event per die newly held (selected -> held). Already-held dice produce no event.

    mark_scoring():
        - Pure state recomputation of scoring_eligible flags; emits no events.

    calculate_selected_score() / selection_is_single_combo():
        - Pure functions; emit no events.
    """

    def __init__(self, game, count: int = 6):
        self.game = game
        self.dice: List[Die] = []
        self.count = count
        self.reset_all()


    # Core dice lifecycle
    def reset_all(self):
        """(Re)create all dice with fresh random values.

        Emits no events (higher level resets already communicate intent via their own events/messages).
        """
        self.dice = [
            Die(
                random.randint(1, 6),
                100 + i * (DICE_SIZE + MARGIN),
                HEIGHT // 2 - DICE_SIZE // 2,
            )
            for i in range(self.count)
        ]

    def roll(self):
        """Roll all non-held dice enforcing the event order contract (see class docstring)."""
        el = self.game.event_listener
        el.publish(GameEvent(GameEventType.PRE_ROLL, payload={}))
        raw_values: list[int] = []
        for idx, d in enumerate(self.dice):
            if not d.held:
                old = d.value
                d.value = random.randint(1, 6)
                d.selected = False
                raw_values.append(d.value)
                el.publish(
                    GameEvent(
                        GameEventType.DIE_ROLLED,
                        payload={"index": idx, "old": old, "new": d.value},
                    )
                )
            else:
                raw_values.append(d.value)
        self.game.locked_after_last_roll = False
        el.publish(GameEvent(GameEventType.POST_ROLL, payload={"values": list(raw_values)}))

    def mark_scoring(self):
        """Recompute scoring_eligible flags for all currently unheld dice.

        Emits no events; callers needing visibility can diff dice state before/after call.
        """
        rules = self.game.rules
        for d in self.dice:
            d.scoring_eligible = False
        unheld = [d for d in self.dice if not d.held]
        if not unheld:
            return
        values = [int(d.value) for d in unheld]
        _, contributing = rules.evaluate(values)
        for i in contributing:
            unheld[i].scoring_eligible = True

    # Helper queries
    def any_scoring_selection(self) -> bool:
        """Return True if at least one currently selected die is scoring-eligible."""
        return any(d.selected and d.scoring_eligible for d in self.dice)

    def selection_values(self) -> list[int]:
        """Return list of face values for currently selected dice (order preserved)."""
        return [int(d.value) for d in self.dice if d.selected]

    def all_held(self) -> bool:
        """Return True if every die is held (hot dice condition)."""
        return all(d.held for d in self.dice)

    def unheld_values(self) -> list[int]:
        """Return list of values for dice that are not held."""
        return [int(d.value) for d in self.dice if not d.held]

    def check_farkle(self) -> bool:
        """Return True if current unheld dice produce zero score (farkle) under rules.

        Returns False if there are no unheld dice (hot dice scenario instead).
        """
        unheld = [d for d in self.dice if not d.held]
        if not unheld:
            return False
        values = [int(d.value) for d in unheld]
        score, _ = self.game.rules.evaluate(values)
        return score == 0

    def hold_selected_publish(self):
        """Hold all selected dice and emit DIE_HELD events for each newly held die."""
        for d in self.dice:
            if d.selected:
                d.hold()
                self.game.event_listener.publish(
                    GameEvent(
                        GameEventType.DIE_HELD,
                        payload={"index": self.dice.index(d), "value": d.value},
                    )
                )

    # Selection scoring
    def calculate_selected_score(self):
        """Return (score, contributing_indices) for the current selection.

        contributing_indices mirror rules.evaluate() contract (relative to the provided list).
        """
        values = self.selection_values()
        if not values:
            return 0, []
        return self.game.rules.evaluate(values)

    # Advanced selection analysis
    def selection_is_single_combo(self) -> bool:
        """Return True if the current selection forms exactly one scoring combo.

        Criteria:
        - All selected dice are covered by exactly one rule match.
        - Among full-coverage matches only those with maximal combo_size are considered; if more
          than one remains it's ambiguous (False).
        - The chosen rule's combo_size equals the number of selected dice.
        """
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
