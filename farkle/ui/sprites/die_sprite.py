import pygame
from farkle.ui.sprites.sprite_base import BaseSprite, Layer
from farkle.dice.die import DICE_SIZE, PIP_POSITIONS

# Local cache reused with same semantics as die._die_surface_cache but sprite-specific (could unify later)
_die_sprite_cache: dict[tuple[int,bool,bool,bool], pygame.Surface] = {}

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
        if game:
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
        d = self.die
        key = (d.value, d.held, d.selected, d.scoring_eligible)
        cached = _die_sprite_cache.get(key)
        if cached is None:
            if d.held:
                color = (200, 80, 80)
            elif d.selected:
                color = (80, 150, 250)
            else:
                color = (230, 230, 230)
            surf = pygame.Surface((DICE_SIZE, DICE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surf, color, surf.get_rect(), border_radius=8)
            pygame.draw.rect(surf, (0,0,0), surf.get_rect(), 3, border_radius=8)
            if not d.held and not d.scoring_eligible:
                surf.set_alpha(130)
            for px, py in PIP_POSITIONS[d.value]:
                pygame.draw.circle(surf, (0,0,0), (px * DICE_SIZE, py * DICE_SIZE), 7)
            _die_sprite_cache[key] = surf
            cached = surf
        self.image = cached
        # Keep rect in sync with logical position
        self.rect.topleft = (d.x, d.y)
        # Reroll highlight overlay (replaces legacy renderer overlay).
        game = getattr(d, 'game', None)
        if game:
            try:
                abm = getattr(game, 'ability_manager', None)
                if abm and abm.selecting_ability() and abm.selecting_ability().id == 'reroll' and not d.held:
                    # Non-held dice get a translucent green overlay.
                    base = self.image
                    highlighted = base.copy()
                    overlay = pygame.Surface(base.get_size(), pygame.SRCALPHA)
                    overlay.fill((60,220,140,90))
                    highlighted.blit(overlay, (0,0))
                    self.image = highlighted
            except Exception:
                pass
        # Mark dirty so a future DirtyLayeredUpdates would re-blit
        self.dirty = 1

__all__ = ["DieSprite"]
