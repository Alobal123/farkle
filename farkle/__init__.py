"""Farkle package public API.

Exports the canonical packaged Game implementation.
Legacy root-level fallback removed.
"""
from __future__ import annotations

from .game import Game  # re-export

__all__ = ["Game"]
