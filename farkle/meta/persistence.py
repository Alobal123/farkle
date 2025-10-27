"""Persistent statistics storage for meta progression across game sessions."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field, asdict


@dataclass
class PersistentStats:
    """Cumulative statistics across all game sessions."""
    
    # Lifetime totals
    total_games_played: int = 0
    total_games_won: int = 0
    total_games_lost: int = 0
    
    # Cumulative stats
    lifetime_gold_gained: int = 0
    lifetime_farkles: int = 0
    lifetime_score: int = 0
    lifetime_turns_played: int = 0
    lifetime_dice_rolled: int = 0
    lifetime_relics_purchased: int = 0
    lifetime_goals_completed: int = 0
    lifetime_levels_completed: int = 0
    
    # Records
    highest_single_score: int = 0
    highest_game_score: int = 0
    most_gold_in_game: int = 0
    most_turns_survived: int = 0
    furthest_level_reached: int = 0
    
    # Meta progression
    faith: int = 0  # Permanent currency earned from priest goals
    total_meta_currency: int = 0
    unlocked_achievements: list[str] = field(default_factory=list)
    
    def merge_session(self, session_stats: dict[str, Any], success: bool, level_index: int) -> None:
        """Merge statistics from a completed game session.
        
        Args:
            session_stats: Statistics summary from StatisticsTracker.export_summary()
            success: Whether the game was won or lost
            level_index: The level/day the player reached
        """
        # Update game counts
        self.total_games_played += 1
        if success:
            self.total_games_won += 1
        else:
            self.total_games_lost += 1
        
        # Merge cumulative stats
        gold_data = session_stats.get('gold', {})
        self.lifetime_gold_gained += gold_data.get('total', 0)
        
        farkle_data = session_stats.get('farkles', {})
        self.lifetime_farkles += farkle_data.get('total', 0)
        
        scoring_data = session_stats.get('scoring', {})
        session_score = scoring_data.get('total_score', 0)
        self.lifetime_score += session_score
        
        # Add faith gained during session
        faith_data = session_stats.get('faith', {})
        self.faith += faith_data.get('total', 0)
        
        gameplay_data = session_stats.get('gameplay', {})
        self.lifetime_turns_played += gameplay_data.get('turns_played', 0)
        self.lifetime_dice_rolled += gameplay_data.get('dice_rolled', 0)
        self.lifetime_relics_purchased += gameplay_data.get('relics_purchased', 0)
        self.lifetime_goals_completed += gameplay_data.get('goals_completed', 0)
        self.lifetime_levels_completed += gameplay_data.get('levels_completed', 0)
        
        # Update records
        session_highest_single = scoring_data.get('highest_single', 0)
        if session_highest_single > self.highest_single_score:
            self.highest_single_score = session_highest_single
        
        if session_score > self.highest_game_score:
            self.highest_game_score = session_score
        
        session_gold = gold_data.get('total', 0)
        if session_gold > self.most_gold_in_game:
            self.most_gold_in_game = session_gold
        
        turns_played = gameplay_data.get('turns_played', 0)
        if turns_played > self.most_turns_survived:
            self.most_turns_survived = turns_played
        
        if level_index > self.furthest_level_reached:
            self.furthest_level_reached = level_index
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersistentStats:
        """Create from dictionary loaded from JSON."""
        # Handle missing fields gracefully for backward compatibility
        return cls(
            total_games_played=data.get('total_games_played', 0),
            total_games_won=data.get('total_games_won', 0),
            total_games_lost=data.get('total_games_lost', 0),
            lifetime_gold_gained=data.get('lifetime_gold_gained', 0),
            lifetime_farkles=data.get('lifetime_farkles', 0),
            lifetime_score=data.get('lifetime_score', 0),
            lifetime_turns_played=data.get('lifetime_turns_played', 0),
            lifetime_dice_rolled=data.get('lifetime_dice_rolled', 0),
            lifetime_relics_purchased=data.get('lifetime_relics_purchased', 0),
            lifetime_goals_completed=data.get('lifetime_goals_completed', 0),
            lifetime_levels_completed=data.get('lifetime_levels_completed', 0),
            highest_single_score=data.get('highest_single_score', 0),
            highest_game_score=data.get('highest_game_score', 0),
            most_gold_in_game=data.get('most_gold_in_game', 0),
            most_turns_survived=data.get('most_turns_survived', 0),
            furthest_level_reached=data.get('furthest_level_reached', 0),
            faith=data.get('faith', 0),
            total_meta_currency=data.get('total_meta_currency', 0),
            unlocked_achievements=data.get('unlocked_achievements', [])
        )


class PersistenceManager:
    """Manages loading and saving persistent statistics to disk."""
    
    def __init__(self, save_path: str | None = None):
        """Initialize the persistence manager.
        
        Args:
            save_path: Path to save file. If None, uses default in user's home directory.
        """
        if save_path is None:
            # Use user's home directory for save file
            home = Path.home()
            save_dir = home / '.farkle'
            save_dir.mkdir(exist_ok=True)
            self.save_path = save_dir / 'stats.json'
        else:
            self.save_path = Path(save_path)
        
        self.stats = self.load()
    
    def load(self) -> PersistentStats:
        """Load statistics from disk, or create new if file doesn't exist."""
        if not self.save_path.exists():
            return PersistentStats()
        
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return PersistentStats.from_dict(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load stats from {self.save_path}: {e}")
            return PersistentStats()
    
    def save(self) -> None:
        """Save current statistics to disk."""
        try:
            # Ensure directory exists
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(self.stats.to_dict(), f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save stats to {self.save_path}: {e}")
    
    def merge_and_save(self, session_stats: dict[str, Any], success: bool, level_index: int) -> None:
        """Merge session statistics and save to disk.
        
        Args:
            session_stats: Statistics summary from StatisticsTracker.export_summary()
            success: Whether the game was won or lost
            level_index: The level/day the player reached
        """
        self.stats.merge_session(session_stats, success, level_index)
        self.save()
    
    def get_stats(self) -> PersistentStats:
        """Get current persistent statistics."""
        return self.stats
    
    def reset(self) -> None:
        """Reset all statistics (useful for debugging/testing)."""
        self.stats = PersistentStats()
        self.save()
