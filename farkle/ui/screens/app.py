import pygame
from typing import Dict, Optional
from .base_screen import Screen
from .game_screen import GameScreen
from .menu_screen import MenuScreen
from .game_over_screen import GameOverScreen
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType

class App:
    """High-level application controller managing screens.

    Screens:
      - 'menu': main menu with New Game button
      - 'game': normal gameplay loop (delegated to Game methods)

    The previous separate ShopScreen has been deprecated: the shop renders as an overlay sprite inside the
    main game screen (SHOP state gates gameplay). This simplifies input routing.
    """
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, clock: pygame.time.Clock):
        """Initialize the App with pygame resources.
        
        Game object creation is deferred until needed (when transitioning to game screen).
        """
        self.screen = screen
        self.font = font
        self.clock = clock
        self.game: Optional[Game] = None
        self.current_name = 'menu'  # Start at menu screen
        self.screens: Dict[str, Screen] = {}
        self._init_screens()

    def _init_screens(self):
        # Initialize persistent screens
        # Menu screen doesn't need game object
        self.screens['menu'] = MenuScreen(self.screen, self.font)
        # Game screen will be created when first needed

    def _on_event(self, event: GameEvent):  # type: ignore[override]
        # Listen for level failed events to transition to game over screen
        if event.type == GameEventType.LEVEL_FAILED:
            # Create game over screen with failure info
            level_name = event.get("level_name", "Unknown")
            level_index = event.get("level_index", 1)
            unfinished = event.get("unfinished", [])
            
            self.screens['game_over'] = GameOverScreen(
                self.screen, 
                self.font,
                success=False,
                level_name=level_name,
                level_index=level_index,
                unfinished_goals=unfinished
            )
            # Transition to game over screen
            self.current_name = 'game_over'
    
    def _ensure_game_initialized(self):
        """Create and initialize game object if not already done."""
        if self.game is None:
            self.game = Game(self.screen, self.font, self.clock, rng_seed=None)
            # Game is auto-initialized by default
            # Subscribe to game events for app-level concerns
            if self.game.event_listener:
                self.game.event_listener.subscribe(self._on_event)
    
    def _ensure_game_screen(self):
        """Create game screen if not already created."""
        if 'game' not in self.screens and self.game:
            self.screens['game'] = GameScreen(self.game)

    def run(self):
        clock = self.clock
        running = True
        while running:
            dt = clock.tick(30) / 1000.0
            
            # Ensure game is initialized if transitioning to game screen
            if self.current_name == 'game':
                self._ensure_game_initialized()
                self._ensure_game_screen()
            
            active = self.screens[self.current_name]
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False; break
                active.handle_event(event)
            
            # Check for screen transitions
            if active.is_done():
                next_screen = active.next_screen()
                
                # If transitioning to menu from game/game_over, reset the game
                if next_screen == 'menu' and self.current_name in ('game', 'game_over'):
                    self.game = None  # Clear game state
                    # Remove game and game_over screens to force recreation on next play
                    self.screens.pop('game', None)
                    self.screens.pop('game_over', None)
                
                if next_screen and (next_screen in self.screens or next_screen in ('game', 'menu')):
                    self.current_name = next_screen
                    # Reset the done state for future transitions
                    from .base_screen import SimpleScreen
                    if isinstance(active, SimpleScreen):
                        active._done = False
                else:
                    # No valid next screen, exit
                    running = False
                    
            active.update(dt)
            active.draw(self.screen)
            pygame.display.flip()
        pygame.quit()

