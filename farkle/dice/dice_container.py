from typing import List
from farkle.dice.die import Die
from farkle.core.game_event import GameEvent, GameEventType
from farkle.ui.settings import WIDTH, HEIGHT, DICE_SIZE, MARGIN
from farkle.ui.sprites.die_sprite import DieSprite  # new sprite bridge


class DiceContainer:
    """Encapsulates dice lifecycle & selection logic."""

    def __init__(self, game, count: int = 6):
        self.game = game
        self.dice: List[Die] = []
        self.count = count
        self.reset_all()

    # --- lifecycle -------------------------------------------------
    def reset_all(self):
        self.dice = []
        # Clear out existing die sprites from groups (if any) by killing them
        renderer = getattr(self.game, 'renderer', None)
        if renderer and hasattr(renderer, 'sprite_groups'):
            # Remove previous dice sprites from layered group
            for spr in list(renderer.sprite_groups['dice']):
                spr.kill()
        # Dynamically calculate total width and starting x-position
        total_width = self.count * DICE_SIZE + (self.count - 1) * MARGIN
        start_x = (WIDTH - total_width) // 2
        for i in range(self.count):
            rng = getattr(self.game, 'rng', None)
            initial_val = rng.randint(1,6) if rng else __import__('random').randint(1,6)
            d = Die(
                initial_val,
                start_x + i * (DICE_SIZE + MARGIN),
                HEIGHT - 360,
            )
            # Attach game reference for sprite gating & highlight logic
            try:
                d.game = self.game
            except Exception:
                pass
            self.dice.append(d)
            # Attach sprite
            if renderer:
                try:
                    ds = DieSprite(d, renderer.sprite_groups['dice'], renderer.layered)
                    # Ensure logical linkage for tests
                    d.sprite = ds
                except Exception:
                    pass

    def roll(self):
        el = self.game.event_listener
        el.publish(GameEvent(GameEventType.PRE_ROLL, payload={}))
        raw_values: list[int] = []
        for idx, d in enumerate(self.dice):
            if not d.held:
                old = d.value
                rng = getattr(self.game, 'rng', None)
                d.value = rng.randint(1,6) if rng else __import__('random').randint(1,6)
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
        # Determine current selection's rule_key and raw score so dice can record combo metadata
        rule_key = None
        raw_score = 0
        try:
            selected_values = self.selection_values()
            if self.game.rules.selection_is_single_combo(selected_values) and self.any_scoring_selection():
                raw_score, _ = self.calculate_selected_score()
                rule_key = self.game.rules.selection_rule_key(selected_values)
        except Exception:
            rule_key = None; raw_score = 0
        for d in self.dice:
            if d.selected:
                d.hold()
                if rule_key and raw_score > 0:
                    d.combo_rule_key = rule_key
                    d.combo_points = raw_score
                self.game.event_listener.publish(GameEvent(GameEventType.DIE_HELD, payload={"index": self.dice.index(d), "value": d.value}))

    # --- scoring helpers -------------------------------------------
    def calculate_selected_score(self):
        values = self.selection_values()
        if not values:
            return 0, []
        total, indices, _ = self.game.rules.evaluate(values)
        return total, indices
