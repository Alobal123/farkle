import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer
from farkle.dice.die import PIP_POSITIONS
from farkle.ui.settings import (
    DICE_SIZE, DICE_SELECTED, DICE_HELD, DICE_NORMAL, DICE_TARGET_SELECTION,
    DICE_BORDER, DICE_PIPS, BORDER_RADIUS_DICE, BORDER_WIDTH_DICE,
    BORDER_WIDTH_TARGET_SELECTION, DICE_PIP_RADIUS_RATIO
)

# Local cache reused with same semantics as die._die_surface_cache but sprite-specific (could unify later)
_die_sprite_cache: dict[tuple[int,bool,bool,bool], pygame.Surface] = {}
_last_dice_size = 0

def _clear_die_cache():
    global _last_dice_size
    _die_sprite_cache.clear()
    _last_dice_size = DICE_SIZE

class DieSprite(BaseSprite):
    """Visual sprite for a logical Die.

    Bridges existing Die object to LayeredUpdates. Keeps rendering identical to Die.draw for now.
    Future improvements: animation, roll tween, glow for scoring eligible, etc.
    """
    def __init__(self, die, *groups):
        super().__init__(Layer.DICE, die, *groups)
        self.die = die
        # Link logical die to its sprite for test/introspection purposes.
        try:
            setattr(die, 'sprite', self)
        except Exception:
            pass
        # Initialize rect at die position
        self.image = pygame.Surface((DICE_SIZE, DICE_SIZE), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(die.x, die.y))
        # Initial visibility gating so tests can inspect without requiring an update() cycle.
        game = getattr(die, 'game', None)
        # Adopt logical die's visible_states for sprite gating.
        self.visible_states = getattr(die, 'visible_states', None)
        try:
            st = game.state_manager.get_state()
            vs = getattr(die, 'visible_states', None)
            if vs is not None and st not in vs:
                self.image = pygame.Surface((1,1), pygame.SRCALPHA)
                self.rect = self.image.get_rect(topleft=(-1000,-1000))
        except Exception:
            pass
        self.sync_from_logical()

    def sync_from_logical(self):  # override
        global _last_dice_size
        if DICE_SIZE != _last_dice_size:
            _clear_die_cache()
        
        d = self.die
        key = (d.value, d.held, d.selected, d.scoring_eligible)
        cached = _die_sprite_cache.get(key)
        if cached is None:
            if d.held:
                color = DICE_HELD
            elif d.selected:
                color = DICE_SELECTED
            else:
                color = DICE_NORMAL
            surf = pygame.Surface((DICE_SIZE, DICE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surf, color, surf.get_rect(), border_radius=BORDER_RADIUS_DICE)
            pygame.draw.rect(surf, DICE_BORDER, surf.get_rect(), BORDER_WIDTH_DICE, border_radius=BORDER_RADIUS_DICE)
            if not d.held and not d.scoring_eligible:
                surf.set_alpha(130)
            for px, py in PIP_POSITIONS[d.value]:
                pip_radius = int(DICE_SIZE * DICE_PIP_RADIUS_RATIO)
                pygame.draw.circle(surf, DICE_PIPS, (px * DICE_SIZE, py * DICE_SIZE), pip_radius)
            _die_sprite_cache[key] = surf
            cached = surf
        self.image = cached
        # Keep rect in sync with logical position
        self.rect.topleft = (d.x, d.y)
        # Ability target selection highlight overlay (unified visual with goal selection)
        game = getattr(d, 'game', None)
        try:
            abm = getattr(game, 'ability_manager', None)
            sel_ab = abm.selecting_ability() if abm else None
            if sel_ab and sel_ab.target_type == 'die' and not d.held:
                # Unified target selection visuals (matching banking selection):
                # - Selected dice: same blue border as banking selection
                base = self.image.copy()
                import pygame as _pg
                die_index = None
                try:
                    die_index = d.game.dice.index(d)
                except Exception:
                    pass
                collected = getattr(sel_ab, 'collected_targets', []) if sel_ab else []
                if die_index is not None and die_index in collected:
                    # Same blue border as banking selection
                    ring = _pg.Surface(base.get_size(), _pg.SRCALPHA)
                    _pg.draw.rect(ring, DICE_TARGET_SELECTION, ring.get_rect(), BORDER_WIDTH_TARGET_SELECTION, border_radius=BORDER_RADIUS_DICE)
                    base.blit(ring, (0,0))
                    self.image = base
        except Exception:
            pass
        # Mark dirty so a future DirtyLayeredUpdates would re-blit
        self.dirty = 1

__all__ = ["DieSprite"]
