import pytest
from unittest.mock import Mock, MagicMock
from farkle.scoring.score_modifiers import RuleSpecificMultiplier, ConditionalScoreModifier
from farkle.scoring.score_types import Score, ScorePart
from farkle.goals.goal import Goal
from farkle.scoring.scoring_manager import ScoringManager


@pytest.fixture
def disaster_goal():
    """A goal that is a disaster."""
    goal = Goal(name="Avert Disaster", target_score=1000, is_disaster=True)
    game_mock = Mock()
    game_mock.scoring_manager.project_goal_pending.return_value = 0
    goal.game = game_mock
    return goal


@pytest.fixture
def petition_goal():
    """A goal that is a petition (not a disaster)."""
    goal = Goal(name="Fulfill Petition", target_score=500, is_disaster=False)
    game_mock = Mock()
    game_mock.scoring_manager.project_goal_pending.return_value = 0
    goal.game = game_mock
    return goal


class DummyGame:
    def __init__(self):
        self.active_goal_index = 0
        self.level_state = Mock()
        self.level_state.goals = []
        self.relic_manager = Mock()
        self.relic_manager.active_relics = []
        self.scoring_manager = ScoringManager(self)


def test_disaster_goal_gets_bonus(disaster_goal):
    """Verify that a disaster-specific modifier applies only to a disaster goal."""
    game = DummyGame()
    game.level_state.goals.append(disaster_goal)
    
    # This modifier should only apply if the goal `is_disaster`
    inner_modifier = RuleSpecificMultiplier(rule_key="111", mult=2.0)
    modifier = ConditionalScoreModifier(inner_modifier, predicate=lambda ctx: getattr(ctx.goal, 'is_disaster', False))
    game.scoring_manager.modifier_chain.add(modifier)
    
    # The score part that the modifier targets
    score_part = ("111", 1000)
    
    # Get the adjusted score from the scoring manager
    result = game.scoring_manager.preview([score_part], goal=disaster_goal)
    adjusted_score = result['adjusted_total']
    
    # The 2.0 multiplier should be applied
    assert adjusted_score == 2000


def test_petition_goal_no_bonus(petition_goal):
    """Verify that a disaster-specific modifier does NOT apply to a non-disaster goal."""
    game = DummyGame()
    game.level_state.goals.append(petition_goal)

    # This modifier should only apply if the goal `is_disaster`
    inner_modifier = RuleSpecificMultiplier(rule_key="111", mult=2.0)
    modifier = ConditionalScoreModifier(inner_modifier, predicate=lambda ctx: getattr(ctx.goal, 'is_disaster', False))
    game.scoring_manager.modifier_chain.add(modifier)

    # The score part that the modifier targets
    score_part = ("111", 1000)

    # Get the adjusted score from the scoring manager
    result = game.scoring_manager.preview([score_part], goal=petition_goal)
    adjusted_score = result['adjusted_total']

    # The 2.0 multiplier should NOT be applied
    assert adjusted_score == 1000
