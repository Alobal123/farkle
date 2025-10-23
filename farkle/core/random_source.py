"""Central randomness source supporting optional seeding.

Usage:
    rng = RandomSource(seed=123)  # deterministic
    v = rng.randint(1,6)
    rng.shuffle(my_list)

Integrate by attaching an instance to Game (e.g. game.rng) and replacing
direct calls to the random module with this wrapper so test suites can
reproduce sequences by supplying a seed.
"""

from __future__ import annotations
import random
from typing import Any, Iterable, Sequence


class RandomSource:
    def __init__(self, seed: int | None = None):
        self._seed = seed
        self._rng = random.Random(seed) if seed is not None else random.Random()

    @property
    def seed(self) -> int | None:
        return self._seed

    def reseed(self, seed: int | None):
        """Reseed RNG (None -> fresh non-deterministic)."""
        self._seed = seed
        if seed is None:
            # Use system randomness
            self._rng = random.Random()
        else:
            self._rng = random.Random(seed)

    # Convenience mirrors of random.Random API (subset used by game)
    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, seq: Sequence[Any]) -> Any:
        return self._rng.choice(seq)

    def shuffle(self, seq: list[Any]) -> None:
        self._rng.shuffle(seq)

    def sample(self, population: Sequence[Any], k: int) -> list[Any]:
        return self._rng.sample(population, k)

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def randrange(self, *args, **kwargs) -> int:  # type: ignore[override]
        return self._rng.randrange(*args, **kwargs)

    def state(self) -> Any:
        """Return internal state (for advanced test assertions)."""
        return self._rng.getstate()

    def set_state(self, state: Any):
        self._rng.setstate(state)
