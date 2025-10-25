"""Test helper utilities for Farkle.

Provides convenience functions to activate relics and ensure their modifiers
are included in the scoring manager chain without relying on event side-effects.
"""
from __future__ import annotations
from typing import Iterable

def ensure_relic_modifiers(game, relics: Iterable):
    """Activate each relic (if not already) and inject its modifiers into scoring manager.

    Idempotent: will not duplicate modifiers (basic identity by class + scalar attrs).
    This bypasses event listener mechanics for lean, fast tests that focus solely on
    scoring outcomes.
    """
    scoring_mgr = getattr(game, 'scoring_manager', None)
    if scoring_mgr is None:
        return
    chain = scoring_mgr.modifier_chain
    # Build a dedupe set from current chain
    existing = set()
    for m in chain.snapshot():
        ident = _modifier_identity(m)
        existing.add(ident)
    for relic in relics:
        try:
            if not getattr(relic, 'active', False):
                relic.activate(game)
        except Exception:
            pass
        try:
            for mod in relic.modifier_chain.snapshot():
                ident = _modifier_identity(mod)
                if ident in existing:
                    continue
                chain.add(mod)
                existing.add(ident)
        except Exception:
            pass


def _modifier_identity(mod) -> tuple:
    keys = []
    # Include inner modifier identity if it's a wrapper
    if hasattr(mod, 'inner'):
        keys.append(_modifier_identity(mod.inner))
    
    # Include predicate source code for conditional modifiers
    if hasattr(mod, 'predicate'):
        try:
            import inspect
            keys.append(inspect.getsource(mod.predicate))
        except (TypeError, OSError):
            # Fallback for built-in or dynamically generated predicates
            keys.append(str(mod.predicate))

    for attr in ('__class__', 'rule_key', 'mult', 'amount', 'priority'):
        if attr == '__class__':
            keys.append(mod.__class__.__name__)
        else:
            if hasattr(mod, attr):
                keys.append(getattr(mod, attr))
            else:
                keys.append(None)
    return tuple(keys)
