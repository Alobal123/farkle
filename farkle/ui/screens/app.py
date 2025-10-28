import pygame
from typing import Dict, Optional
from .base_screen import Screen
from .game_screen import GameScreen
from .menu_screen import MenuScreen
from .game_over_screen import GameOverScreen
from .statistics_screen import StatisticsScreen
from farkle.game import Game
from farkle.core.game_event import GameEvent, GameEventType
from farkle.meta.persistence import PersistenceManager
from farkle.meta.save_manager import SaveManager

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
        
        # Initialize persistence manager for cross-session statistics
        self.persistence = PersistenceManager()
        
        # Initialize save manager for game state autosave
        self.save_manager = SaveManager()
        
        self._init_screens()

    def _init_screens(self):
        # Initialize persistent screens
        # Menu screen doesn't need game object, but needs to know if save exists
        has_save = self.save_manager.has_save()
        self.screens['menu'] = MenuScreen(self.screen, self.font, has_save=has_save)
        # Game screen will be created when first needed

    def _on_event(self, event: GameEvent):  # type: ignore[override]
        # Listen for level failed events to transition to game over screen
        if event.type == GameEventType.LEVEL_FAILED:
            # Create game over screen with failure info
            level_name = event.get("level_name", "Unknown")
            level_index = event.get("level_index", 1)
            unfinished = event.get("unfinished", [])
            
            # Get statistics from the game if available
            statistics = {}
            if self.game and hasattr(self.game, 'statistics_tracker'):
                statistics = self.game.statistics_tracker.export_summary()
            
            # Merge session statistics into persistent storage
            self.persistence.merge_and_save(
                session_stats=statistics,
                success=False,  # LEVEL_FAILED means game lost
                level_index=level_index
            )
            
            self.screens['game_over'] = GameOverScreen(
                self.screen, 
                self.font,
                success=False,
                level_name=level_name,
                level_index=level_index,
                unfinished_goals=unfinished,
                statistics=statistics
            )
            # Transition to game over screen
            self.current_name = 'game_over'
    
    def _ensure_game_initialized(self, load_save: bool = False):
        """Create and initialize game object if not already done.
        
        Args:
            load_save: If True, attempt to load game from save file
        """
        if self.game is None:
            # Skip god selection when loading from save
            self.game = Game(self.screen, self.font, self.clock, rng_seed=None, skip_god_selection=load_save)
            # Game is auto-initialized by default
            
            # Load saved state if requested
            if load_save:
                save_data = self.save_manager.load()
                if save_data:
                    self.save_manager.restore_game_state(self.game, save_data)
            
            # Subscribe to game events for app-level concerns
            if self.game.event_listener:
                self.game.event_listener.subscribe(self._on_event)
            # Attach save manager for autosave
            self.save_manager.attach(self.game)
    
    def _ensure_game_screen(self):
        """Create game screen if not already created."""
        if 'game' not in self.screens and self.game:
            self.screens['game'] = GameScreen(self.game)
    
    def _ensure_statistics_screen(self):
        """Create or refresh statistics screen with latest data."""
        # Always recreate to show fresh stats
        stats = self.persistence.get_stats()
        self.screens['statistics'] = StatisticsScreen(self.screen, self.font, stats)

    def run(self):
        clock = self.clock
        running = True
        while running:
            dt = clock.tick(30) / 1000.0
            
            # Ensure game is initialized if transitioning to game screen
            if self.current_name == 'game':
                self._ensure_game_initialized(load_save=False)
                self._ensure_game_screen()
            
            # Ensure game is initialized from save if continuing
            if self.current_name == 'continue_game':
                self._ensure_game_initialized(load_save=True)
                self._ensure_game_screen()
                self.current_name = 'game'  # Redirect to game screen
            
            # Ensure statistics screen is created/refreshed when transitioning to it
            if self.current_name == 'statistics':
                self._ensure_statistics_screen()
            
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
                    # Delete save file when returning to menu (game over)
                    self.save_manager.delete_save()
                    self.game = None  # Clear game state
                    # Remove game and game_over screens to force recreation on next play
                    self.screens.pop('game', None)
                    self.screens.pop('game_over', None)
                    # Recreate menu screen with updated save status
                    has_save = self.save_manager.has_save()
                    self.screens['menu'] = MenuScreen(self.screen, self.font, has_save=has_save)
                
                # Handle statistics screen transitions
                if next_screen == 'statistics':
                    self._ensure_statistics_screen()
                
                if next_screen and (next_screen in self.screens or next_screen in ('game', 'menu', 'statistics', 'continue_game')):
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

