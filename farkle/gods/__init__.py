"""Gods package - Divine progression system.

Each god levels up through specific thematic achievements:
- Demeter: Nature goal completions
- Ares: Warfare goal completions  
- Hades: Spirit goal completions
- Hermes: Commerce goal completions
"""

from farkle.gods.gods_manager import God, GodsManager
from farkle.gods.demeter import Demeter
from farkle.gods.ares import Ares
from farkle.gods.hades import Hades
from farkle.gods.hermes import Hermes

__all__ = [
    "God",
    "GodsManager", 
    "Demeter",
    "Ares",
    "Hades",
    "Hermes",
]
