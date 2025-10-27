"""Statistics tracker that records game events for meta progression.

This component listens to all game events and maintains running statistics
that can be used for achievements, upgrades, and other meta-progression features.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from farkle.core.game_event import GameEvent, GameEventType

if TYPE_CHECKING:
    from farkle.game import Game


@dataclass
class GameStatistics:
    """Container for statistics from a single game session."""
    
    # Gold tracking
    total_gold_gained: int = 0
    gold_events: list[dict[str, Any]] = field(default_factory=list)
    
    # Faith tracking
    total_faith_gained: int = 0
    faith_events: list[dict[str, Any]] = field(default_factory=list)
    
    # Farkle tracking
    total_farkles: int = 0
    farkle_events: list[dict[str, Any]] = field(default_factory=list)
    
    # Scoring tracking
    total_score: int = 0
    score_events: list[dict[str, Any]] = field(default_factory=list)
    highest_single_score: int = 0
    
    # Additional useful stats
    turns_played: int = 0
    dice_rolled: int = 0
    relics_purchased: int = 0
    goals_completed: int = 0
    levels_completed: int = 0
    
    def add_gold_event(self, event: GameEvent) -> None:
        """Record a gold gain event."""
        amount = event.get('amount', 0)
        source = event.get('source', 'unknown')
        goal_name = event.get('goal_name', '')
        goal_category = event.get('goal_category', '')
        god_name = event.get('god_name', '')
        
        self.total_gold_gained += amount
        self.gold_events.append({
            'amount': amount,
            'source': source,
            'goal_name': goal_name,
            'goal_category': goal_category,
            'god_name': god_name,
            'total_after': self.total_gold_gained
        })
    
    def add_faith_event(self, event: GameEvent) -> None:
        """Record a faith gain event."""
        amount = event.get('amount', 0)
        source = event.get('source', 'unknown')
        goal_name = event.get('goal_name', '')
        god_name = event.get('god_name', '')
        
        self.total_faith_gained += amount
        self.faith_events.append({
            'amount': amount,
            'source': source,
            'goal_name': goal_name,
            'god_name': god_name,
            'total_after': self.total_faith_gained
        })
    
    def add_farkle_event(self, event: GameEvent) -> None:
        """Record a farkle event."""
        self.total_farkles += 1
        self.farkle_events.append({
            'turn': self.turns_played,
            'farkle_count': self.total_farkles
        })
    
    def add_score_event(self, event: GameEvent) -> None:
        """Record a score application event."""
        adjusted = event.get('adjusted', 0)
        raw = event.get('raw', 0)
        rule_key = event.get('rule_key', 'unknown')
        
        self.total_score += adjusted
        if adjusted > self.highest_single_score:
            self.highest_single_score = adjusted
        
        self.score_events.append({
            'adjusted': adjusted,
            'raw': raw,
            'rule_key': rule_key,
            'total_after': self.total_score
        })
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all statistics."""
        return {
            'gold': {
                'total': self.total_gold_gained,
                'events_count': len(self.gold_events)
            },
            'farkles': {
                'total': self.total_farkles,
                'events_count': len(self.farkle_events)
            },
            'scoring': {
                'total_score': self.total_score,
                'highest_single': self.highest_single_score,
                'events_count': len(self.score_events)
            },
            'faith': {
                'total': self.total_faith_gained,
                'events_count': len(self.faith_events)
            },
            'gameplay': {
                'turns_played': self.turns_played,
                'dice_rolled': self.dice_rolled,
                'relics_purchased': self.relics_purchased,
                'goals_completed': self.goals_completed,
                'levels_completed': self.levels_completed
            }
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize statistics for saving."""
        return {
            'total_gold_gained': self.total_gold_gained,
            'total_faith_gained': self.total_faith_gained,
            'total_farkles': self.total_farkles,
            'total_score': self.total_score,
            'highest_single_score': self.highest_single_score,
            'turns_played': self.turns_played,
            'dice_rolled': self.dice_rolled,
            'relics_purchased': self.relics_purchased,
            'goals_completed': self.goals_completed,
            'levels_completed': self.levels_completed,
            # Save event lists for detailed history
            'gold_events': self.gold_events,
            'faith_events': self.faith_events,
            'farkle_events': self.farkle_events,
            'score_events': self.score_events
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameStatistics":
        """Restore statistics from saved data."""
        stats = cls()
        stats.total_gold_gained = data.get('total_gold_gained', 0)
        stats.total_faith_gained = data.get('total_faith_gained', 0)
        stats.total_farkles = data.get('total_farkles', 0)
        stats.total_score = data.get('total_score', 0)
        stats.highest_single_score = data.get('highest_single_score', 0)
        stats.turns_played = data.get('turns_played', 0)
        stats.dice_rolled = data.get('dice_rolled', 0)
        stats.relics_purchased = data.get('relics_purchased', 0)
        stats.goals_completed = data.get('goals_completed', 0)
        stats.levels_completed = data.get('levels_completed', 0)
        # Restore event lists
        stats.gold_events = data.get('gold_events', [])
        stats.faith_events = data.get('faith_events', [])
        stats.farkle_events = data.get('farkle_events', [])
        stats.score_events = data.get('score_events', [])
        return stats


class StatisticsTracker:
    """Tracks game statistics by listening to events.
    
    This component automatically subscribes to the game's event listener
    and records relevant events for later analysis, achievements, and
    meta-progression features.
    """
    
    def __init__(self, game: Game):
        """Initialize the statistics tracker.
        
        Args:
            game: Game instance to track
        """
        self.game = game
        self.current_session = GameStatistics()
        
        # Subscribe to all events
        self.game.event_listener.subscribe(self.on_event)
    
    def on_event(self, event: GameEvent) -> None:
        """Handle incoming game events and update statistics.
        
        Args:
            event: The game event to process
        """
        # Gold tracking
        if event.type == GameEventType.GOLD_GAINED:
            self.current_session.add_gold_event(event)
        
        # Faith tracking
        elif event.type == GameEventType.FAITH_GAINED:
            self.current_session.add_faith_event(event)
        
        # Farkle tracking
        elif event.type == GameEventType.FARKLE:
            self.current_session.add_farkle_event(event)
        
        # Scoring tracking
        elif event.type == GameEventType.SCORE_APPLIED:
            self.current_session.add_score_event(event)
        
        # Additional event tracking
        # Track TURN_END instead of TURN_START to avoid counting the initial setup turn
        elif event.type == GameEventType.TURN_END:
            self.current_session.turns_played += 1
        
        elif event.type == GameEventType.DIE_ROLLED:
            self.current_session.dice_rolled += 1
        
        elif event.type == GameEventType.RELIC_PURCHASED:
            self.current_session.relics_purchased += 1
        
        elif event.type == GameEventType.GOAL_FULFILLED:
            self.current_session.goals_completed += 1
        
        elif event.type == GameEventType.LEVEL_COMPLETE:
            self.current_session.levels_completed += 1
    
    def get_statistics(self) -> GameStatistics:
        """Get the current session statistics.
        
        Returns:
            Current game statistics
        """
        return self.current_session
    
    def reset(self) -> None:
        """Reset statistics for a new game session."""
        self.current_session = GameStatistics()
    
    def export_summary(self) -> dict[str, Any]:
        """Export a summary of current statistics.
        
        Returns:
            Dictionary with summary of all tracked statistics
        """
        return self.current_session.get_summary()
