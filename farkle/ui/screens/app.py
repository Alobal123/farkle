import pygame
from typing import Dict, Optional
from .base_screen import Screen
from .game_screen import GameScreen
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType

class App:
    """High-level application controller managing screens.

    Screens:
      - 'game': normal gameplay loop (delegated to Game methods)

    The previous separate ShopScreen has been deprecated: the shop renders as an overlay sprite inside the
    main game screen (SHOP state gates gameplay). This simplifies input routing.
    """
    def __init__(self, game: Game):
        self.game = game
        self.current_name = 'game'
        self.screens: Dict[str, Screen] = {}
        self._init_screens()
        # Listen for level advancement finishing to open shop
        self.game.event_listener.subscribe(self._on_event)

    def _init_screens(self):
        # Initialize persistent screens
        self.screens['game'] = GameScreen(self.game)
        # ShopScreen removed; shop now renders as overlay within GameScreen.

    def _on_event(self, event: GameEvent):  # type: ignore[override]
        # No screen switching required; overlay sprite reacts within GameScreen.
        return

    def run(self):
        clock = self.game.clock
        running = True
        while running:
            dt = clock.tick(30) / 1000.0
            active = self.screens[self.current_name]
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False; break
                active.handle_event(event)
            active.update(dt)
            active.draw(self.game.screen)
            pygame.display.flip()
        pygame.quit()

