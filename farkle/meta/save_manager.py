"""Autosave system for game state persistence."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING
from farkle.core.game_event import GameEvent, GameEventType
from farkle.goals.goal import Goal

if TYPE_CHECKING:
    from farkle.game import Game


class SaveManager:
    """Manages automatic saving and loading of game state."""
    
    def __init__(self, save_path: str | None = None):
        """Initialize the save manager.
        
        Args:
            save_path: Path to save file. If None, uses default in user's home directory.
        """
        if save_path is None:
            # Use user's home directory for save file
            home = Path.home()
            save_dir = home / '.farkle'
            save_dir.mkdir(exist_ok=True)
            self.save_path = save_dir / 'savegame.json'
        else:
            self.save_path = Path(save_path)
        
        self.game: Game | None = None
        self._auto_save_enabled = True
    
    def attach(self, game: Game) -> None:
        """Attach to a game instance and subscribe to events.
        
        Args:
            game: Game instance to monitor for autosave
        """
        self.game = game
        if game.event_listener:
            # Subscribe to events that trigger autosave
            game.event_listener.subscribe(self.on_event, types={
                GameEventType.TURN_END,
                GameEventType.LEVEL_COMPLETE,
                GameEventType.GOAL_FULFILLED,
                GameEventType.RELIC_PURCHASED,
                GameEventType.SHOP_CLOSED,
            })
    
    def on_event(self, event: GameEvent) -> None:
        """Handle game events for autosave triggers."""
        if not self._auto_save_enabled or not self.game:
            return
        
        # Save on significant events
        if event.type in (
            GameEventType.TURN_END,
            GameEventType.LEVEL_COMPLETE,
            GameEventType.GOAL_FULFILLED,
            GameEventType.SHOP_CLOSED,
            GameEventType.RELIC_PURCHASED,
        ):
            self.save()
    
    def save(self) -> bool:
        """Save current game state to disk.
        
        Returns:
            True if save successful, False otherwise
        """
        if not self.game:
            return False
        
        try:
            save_data = self._serialize_game_state()
            
            # Ensure directory exists
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Warning: Could not save game to {self.save_path}: {e}")
            return False
    
    def load(self) -> dict[str, Any] | None:
        """Load game state from disk.
        
        Returns:
            Saved game data dict, or None if no save exists or error
        """
        if not self.save_path.exists():
            return None
        
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load save from {self.save_path}: {e}")
            return None
    
    def has_save(self) -> bool:
        """Check if a save file exists.
        
        Returns:
            True if save file exists and is readable
        """
        return self.save_path.exists()
    
    def delete_save(self) -> bool:
        """Delete the save file.
        
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            if self.save_path.exists():
                self.save_path.unlink()
            return True
        except Exception as e:
            print(f"Warning: Could not delete save at {self.save_path}: {e}")
            return False
    
    def _serialize_game_state(self) -> dict[str, Any]:
        """Serialize current game state to dictionary.
        
        Returns:
            Dictionary containing all necessary game state
        """
        game = self.game
        if not game:
            return {}
        
        # Player state
        player_data = game.player.to_dict()
        
        # Level state
        level_data = {
            'level_index': game.level_index,
            'level_name': game.level.name if game.level else '',
            'turns_left': game.level_state.turns_left if game.level_state else 3,
            'goals': [
                goal.to_dict()
                for goal in (game.level_state.goals if game.level_state else [])
            ],
            'completed': game.level_state.completed if game.level_state else False,
            'failed': game.level_state.failed if game.level_state else False,
        }
        
        # Relics
        relics_data = [
            {
                'name': relic.name,
                'type': relic.__class__.__name__,
            }
            for relic in game.relic_manager.active_relics
        ]
        
        # Gods data
        gods_data = {
            'worshipped': [
                {
                    'name': god.name,
                    'level': god.level,
                }
                for god in game.gods.worshipped
            ],
        }
        
        # Current turn state
        turn_data = {
            'turn_score': game.turn_score,
            'current_roll_score': game.current_roll_score,
            'locked_after_last_roll': game.locked_after_last_roll,
            'active_goal_index': game.active_goal_index,
        }
        
        # Game state
        state_data = {
            'state': game.state_manager.get_state().name if game.state_manager else 'PRE_ROLL',
        }
        
        # Abilities state
        abilities_data = []
        if hasattr(game, 'ability_manager'):
            for ability in game.ability_manager.abilities:
                abilities_data.append({
                    'id': ability.id,
                    'charges_used': ability.charges_used,
                })
        
        # Statistics
        statistics_data = {}
        if hasattr(game, 'statistics_tracker') and game.statistics_tracker:
            statistics_data = game.statistics_tracker.current_session.to_dict()
        
        return {
            'version': '1.0',
            'player': player_data,
            'level': level_data,
            'relics': relics_data,
            'gods': gods_data,
            'turn': turn_data,
            'state': state_data,
            'abilities': abilities_data,
            'statistics': statistics_data,
        }
    
    def restore_game_state(self, game: Game, save_data: dict[str, Any]) -> bool:
        """Restore game state from saved data.
        
        Args:
            game: Game instance to restore state into
            save_data: Saved game data dictionary
            
        Returns:
            True if restoration successful, False otherwise
        """
        try:
            # Restore player state (using Player's serialization methods)
            player_data = save_data.get('player', {})
            game.player.gold = player_data.get('gold', 0)
            game.player.faith = player_data.get('faith', 0)
            game.player.temple_income = player_data.get('temple_income', 30)
            
            # Restore active effects (blessings/curses) - complex restoration handled separately
            effects_data = player_data.get('active_effects', [])
            self._restore_active_effects(game, effects_data)
            
            # Restore level state
            level_data = save_data.get('level', {})
            game.level_index = level_data.get('level_index', 1)
            if game.level_state:
                game.level_state.turns_left = level_data.get('turns_left', 3)
                game.level_state.completed = level_data.get('completed', False)
                game.level_state.failed = level_data.get('failed', False)
            
            # Restore goals
            goals_data = level_data.get('goals', [])
            if game.level_state:
                for i, goal_data in enumerate(goals_data):
                    if i < len(game.level_state.goals):
                        game.level_state.goals[i].update_from_dict(goal_data)
            
            # Restore relics
            relics_data = save_data.get('relics', [])
            self._restore_relics(game, relics_data)
            
            # Restore gods
            gods_data = save_data.get('gods', {})
            self._restore_gods(game, gods_data)
            
            # Restore turn state
            turn_data = save_data.get('turn', {})
            game.turn_score = turn_data.get('turn_score', 0)
            game.current_roll_score = turn_data.get('current_roll_score', 0)
            game.locked_after_last_roll = turn_data.get('locked_after_last_roll', False)
            game.active_goal_index = turn_data.get('active_goal_index', 0)
            
            # Restore abilities state
            abilities_data = save_data.get('abilities', [])
            if hasattr(game, 'ability_manager'):
                for ability_data in abilities_data:
                    ability = game.ability_manager.get(ability_data.get('id'))
                    if ability:
                        ability.charges_used = ability_data.get('charges_used', 0)
            
            # Restore statistics
            statistics_data = save_data.get('statistics', {})
            if hasattr(game, 'statistics_tracker') and game.statistics_tracker and statistics_data:
                from farkle.meta.statistics_tracker import GameStatistics
                game.statistics_tracker.current_session = GameStatistics.from_dict(statistics_data)
            
            # Restore game state
            state_data = save_data.get('state', {})
            state_name = state_data.get('state', 'PRE_ROLL')
            self._restore_game_state(game, state_name)
            
            return True
        except Exception as e:
            print(f"Warning: Could not restore game state: {e}")
            return False
    
    def _restore_active_effects(self, game: Game, effects_data: list[dict[str, Any]]) -> None:
        """Restore active effects (blessings/curses) to player."""
        # Clear existing effects
        for effect in list(game.player.active_effects):
            try:
                game.player.remove_effect(effect)
            except Exception:
                pass
        game.player.active_effects.clear()
        
        # Restore saved effects
        for effect_data in effects_data:
            effect_type = effect_data.get('type')
            
            try:
                # Currently only DoubleScoreBlessing is implemented
                if effect_type == 'DoubleScoreBlessing':
                    from farkle.blessings import DoubleScoreBlessing
                    
                    # Get the remaining duration from save data
                    # The duration field in TemporaryEffect stores remaining turns
                    remaining_duration = effect_data.get('duration', 1)
                    
                    # Create blessing with remaining duration
                    blessing = DoubleScoreBlessing(duration=remaining_duration)
                    
                    # Add to player and activate
                    game.player.active_effects.append(blessing)
                    # Set player reference before activation
                    object.__setattr__(blessing, 'player', game.player)
                    blessing.activate(game)
                    
            except Exception as e:
                print(f"Warning: Could not restore effect {effect_type}: {e}")
    
    def _restore_relics(self, game: Game, relics_data: list[dict[str, Any]]) -> None:
        """Restore purchased relics."""
        import inspect
        from farkle.relics import relic as relic_module
        
        # Automatically discover all Relic subclasses from the relic module
        relic_classes = {}
        for name, obj in inspect.getmembers(relic_module, inspect.isclass):
            # Check if it's a subclass of Relic (but not Relic itself)
            if (hasattr(relic_module, 'Relic') and 
                issubclass(obj, relic_module.Relic) and 
                obj is not relic_module.Relic):
                relic_classes[name] = obj
        
        # Clear existing relics and re-purchase from save
        game.relic_manager.active_relics.clear()
        
        for relic_data in relics_data:
            relic_type = relic_data.get('type')
            if relic_type in relic_classes:
                try:
                    relic = relic_classes[relic_type]()
                    relic.activate(game)
                    game.relic_manager.active_relics.append(relic)
                except Exception as e:
                    print(f"Warning: Could not restore relic {relic_type}: {e}")
    
    def _restore_gods(self, game: Game, gods_data: dict[str, Any]) -> None:
        """Restore worshipped gods and their progression."""
        from farkle.gods.gods_manager import God
        
        worshipped_data = gods_data.get('worshipped', [])
        
        # Restore worshipped gods
        restored_gods = []
        for god_data in worshipped_data:
            god = God(god_data.get('name', 'Unknown'), game)
            god.level = god_data.get('level', 1)
            restored_gods.append(god)
        
        if restored_gods:
            game.gods.set_worshipped(restored_gods)
    
    def _restore_game_state(self, game: Game, state_name: str) -> None:
        """Restore game state enum."""
        if not game.state_manager:
            return
        
        from farkle.core.game_state_enum import GameState
        
        # Use enum's __members__ to get state by name
        try:
            state = GameState[state_name]
            game.state_manager.set_state(state)
        except (KeyError, Exception):
            # If state name is invalid or setting fails, ignore
            pass
