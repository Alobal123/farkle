"""Quick test to verify level progression with optional goals."""

from farkle.level.level import Level
from farkle.core.random_source import RandomSource

# Use a seeded RNG for reproducible results
rng = RandomSource(seed=42)

# Create initial level
level1 = Level.single("Invocation Rite", 300, 2, "First rite", rng=rng)
print(f"\n=== Level 1: {level1.name} ===")
print(f"Max turns: {level1.max_turns}")
print(f"Goals ({len(level1.goals)}):")
for i, (name, target, mandatory, reward_gold, reward_income, reward_blessing, flavor, category, persona, reward_faith) in enumerate(level1.goals):
    goal_type = "MANDATORY" if mandatory else "optional"
    reward_str = f"{reward_gold}g" if reward_gold > 0 else ""
    if reward_income > 0:
        reward_str += f" +{reward_income} income" if reward_str else f"+{reward_income} income"
    if reward_blessing:
        reward_str += f" {reward_blessing} blessing" if reward_str else f"{reward_blessing} blessing"
    if reward_faith > 0:
        reward_str += f" +{reward_faith} faith" if reward_str else f"+{reward_faith} faith"
    print(f"  {i+1}. [{goal_type}] {name}: {target} points, {reward_str} (category: {category}, persona: {persona})")

# Advance through several levels to show progression
current_level = level1
for level_idx in range(2, 9):
    current_level = Level.advance(current_level, level_idx, rng=rng)
    print(f"\n=== Level {level_idx}: {current_level.name} ===")
    print(f"Max turns: {current_level.max_turns}")
    
    # Count optional vs mandatory
    mandatory_count = sum(1 for _, _, m, _, _, _, _, _, _, _ in current_level.goals if m)
    optional_count = sum(1 for _, _, m, _, _, _, _, _, _, _ in current_level.goals if not m)
    
    print(f"Goals ({len(current_level.goals)} total: {mandatory_count} mandatory, {optional_count} optional):")
    for i, (name, target, mandatory, reward_gold, reward_income, reward_blessing, flavor, category, persona, reward_faith) in enumerate(current_level.goals):
        goal_type = "MANDATORY" if mandatory else "optional"
        reward_str = f"{reward_gold}g" if reward_gold > 0 else ""
        if reward_income > 0:
            reward_str += f" +{reward_income} income" if reward_str else f"+{reward_income} income"
        if reward_blessing:
            reward_str += f" {reward_blessing} blessing" if reward_str else f"{reward_blessing} blessing"
        if reward_faith > 0:
            reward_str += f" +{reward_faith} faith" if reward_str else f"+{reward_faith} faith"
        print(f"  {i+1}. [{goal_type}] {name}: {target} points, {reward_str} (category: {category}, persona: {persona})")

print("\n=== Progression Summary ===")
print("Expected optional goal counts:")
print("Level 1: 2 optional")
print("Level 2: 2 optional")
print("Level 3: 3 optional")
print("Level 4: 3 optional")
print("Level 5: 4 optional")
print("Level 6+: 4 optional (capped)")
