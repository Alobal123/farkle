import pygame
from enum import IntEnum

class Layer(IntEnum):
    BACKGROUND = 0
    WORLD = 50
    DICE = 100
    UI = 200
    OVERLAY = 300
    MODAL = 400
    TOOLTIP = 450
    DEBUG = 900

class BaseSprite(pygame.sprite.Sprite):
    """Minimal sprite base with layer + optional reference to logical object.

    This decouples rendering placement (image/rect) from game logic objects (Die, Relic, etc.).
    Logical objects can either:
      1. Own a sprite (preferred going forward) OR
      2. Lazily create one when first drawn (bridge phase).

    For now we keep sprite very lightweight; animation/tween hooks can be added later.
    """
    def __init__(self, layer: int, logical=None, *groups):
        super().__init__(*groups)
        self._layer = layer  # honored by LayeredUpdates
        self.logical = logical  # pointer back to domain object (Die, etc.)
        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        # Dirty flag placeholder if we adopt DirtySprite optimization later
        self.dirty = 1
        # Optional visibility gating (mirrors GameObject pattern). Subclasses can set these.
        self.visible_states = None  # set to a set of GameState values
        self.visible_predicate = None  # callable(game) -> bool
        # Debug construction print removed (was noisy during development). If needed, instrument here.

    def sync_from_logical(self):  # to be overridden by subclasses
        pass

    def update(self, *args, **kwargs):  # pygame calls each frame if group.update() used
        # Enforce optional visibility gating before syncing logic.
        game = None
        try:
            # Attempt to obtain game from logical object if present
            game = getattr(self.logical, 'game', None)
        except Exception:
            game = None
        if game and (self.visible_states or self.visible_predicate):
            try:
                st = game.state_manager.get_state()
                allowed = True
                if self.visible_states and st not in self.visible_states:
                    allowed = False
                if allowed and self.visible_predicate and not self.visible_predicate(game):
                    allowed = False
                if not allowed:
                    # Hide sprite; keep off-screen to avoid interaction
                    if self.image.get_width() != 1 or self.image.get_height() != 1:
                        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
                        self.rect = self.image.get_rect(topleft=(-1000,-1000))
                    else:
                        self.image.fill((0,0,0,0))
                    self.dirty = 1
                    return
            except Exception:
                pass
        if self.logical is not None:
            self.sync_from_logical()

__all__ = ["Layer", "BaseSprite"]
