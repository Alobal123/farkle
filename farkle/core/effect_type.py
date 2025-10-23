from enum import Enum, auto

class EffectType(Enum):
    """Categorizes temporary effects as beneficial or detrimental."""
    BLESSING = auto()
    CURSE = auto()
